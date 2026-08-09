"""
Import one Rankmax project (a Mongo `group`) into PromptMaxx as a Domain with
its keywords and full rank history.

    manage.py import_rankmax_project --group-id 6720 --dry-run
    manage.py import_rankmax_project --group-id 6720

SEO data only. Every GEO-monitoring field is deliberately left at its default:
no prompts, no topics, no brand identity, no competitor analysis. Two flags
carry that intent and matter more than they look:

  Keyword.auto_generate_prompts = False
      The model default is True. Left at True, ~21k imported keywords would
      feed the GEO prompt-generation pipeline and spend OpenRouter credit.

  SeoKeywordRank.auto_call_status = 'done'
      'avail' is the engine's crawl queue (see seo_rankings/views.py:763).
      Imported rows must NOT re-enter it — the history is already here, and
      21k keywords entering the daily SERP queue is a real bill.

Neither is cosmetic; both are cost controls.

RANK HISTORY — how dates are derived
------------------------------------
Rankmax stores history as a bare array of ints on each keyword, with no dates:
`rank: [1, 1, 2, 0, ...]`. Position is implied by index, and the array runs
BACKWARDS from the most recent crawl:

    date(index i) = keyword.created_date.date() + (len - 1 - i) days

so index 0 is the latest day and index len-1 is created_date. The span was
verified across 147 keywords spanning all 49 PivotRoots projects: every one
implies the same final date (2026-08-09) despite created_date ranging over two
years and array lengths from 12 to 796. The Crocs project proves it inside a
single project — two cohorts created three days apart differ by exactly three
entries and share an end date. The series is therefore a daily append with no
gaps, which is what makes an index-derived date trustworthy.

The array is stored NEWEST FIRST — index 0 is the most recent crawl. Verified
on 101 keywords across three projects: `ranknow` equals rank[0] in 101 cases
and rank[-1] in only 55. Reading it the other way silently reverses every
history series, which is easy to miss on a project whose positions barely move
(YCH sits at rank 1 on 26 of 27 keywords, so both ends of its array are
identical and the direction is undetectable there). Validate direction on a
project with movement.

So the current position is rank[0], not rank[-1], and it agrees with `ranknow`.
"""
import datetime
import json
from collections import Counter

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from domains.models import Domain
from keywords.models import Keyword
from seo_rankings.models import SeoDomainDailyMetrics, SeoKeywordRank, SeoRankHistory

# Rankmax Mongo. Read-only; the import never writes to the source.
MONGO = {
    "host": "128.199.31.183",
    "port": 21012,
    "username": "mysteryadmin",
    "authSource": "mystery_dev_2024",
    "db": "mystery_dev_2024",
}

# Two-letter Rankmax isocode -> the country name Domain.country expects.
ISO_TO_COUNTRY = {
    "in": "India", "us": "United States", "gb": "United Kingdom", "uk": "United Kingdom",
    "ae": "United Arab Emirates", "sa": "Saudi Arabia", "qa": "Qatar", "kw": "Kuwait",
    "om": "Oman", "bh": "Bahrain", "sg": "Singapore", "my": "Malaysia", "id": "Indonesia",
    "au": "Australia", "ca": "Canada", "hk": "Hong Kong", "lk": "Sri Lanka",
}

# Fields copied straight across from the Mongo keyword doc.
PLATFORMS = {"desktop", "mobile"}


class Command(BaseCommand):
    help = "Import one Rankmax project (group) into PromptMaxx as a Domain + keywords + rank history."

    def add_arguments(self, parser):
        parser.add_argument("--group-id", type=int, required=True,
                            help="Rankmax group.id, e.g. 6720 for YCH")
        parser.add_argument("--org", type=int, default=1,
                            help="Target organisation id (default 1, PivotRoots)")
        parser.add_argument("--dry-run", action="store_true",
                            help="Report exactly what would be written, then roll back.")
        parser.add_argument("--history-days", type=int, default=0,
                            help="Keep only the most recent N days of rank history (0 = all).")
        parser.add_argument("--skip-metrics", action="store_true",
                            help="Do not backfill SeoDomainDailyMetrics (the overview cards).")
        parser.add_argument("--skip-history", action="store_true",
                            help="Import the project and keywords but no rank history.")
        parser.add_argument("--from-json", type=str, default="",
                            help="Read the group from a JSON export instead of MongoDB "
                                 "(use when pymongo is unavailable).")
        parser.add_argument("--mongo-password", type=str, default="",
                            help="Override the Mongo password (defaults to RANKMAX_MONGO_PASSWORD in .env).")

    # ------------------------------------------------------------------ source

    def _load_from_mongo(self, group_id, password):
        try:
            import pymongo
        except ImportError:
            raise CommandError(
                "pymongo is not installed in this environment.\n"
                "Either install it, or export the group to JSON on a host that has it "
                "and re-run with --from-json <file>."
            )
        password = password or getattr(settings, "RANKMAX_MONGO_PASSWORD", "") or ""
        if not password:
            raise CommandError(
                "No Mongo password. Pass --mongo-password or set RANKMAX_MONGO_PASSWORD in .env."
            )
        client = pymongo.MongoClient(
            host=MONGO["host"], port=MONGO["port"], username=MONGO["username"],
            password=password, authSource=MONGO["authSource"],
            serverSelectionTimeoutMS=20000,
        )
        db = client[MONGO["db"]]
        group = db.group.find_one({"id": group_id})
        if not group:
            raise CommandError(f"No Rankmax group with id={group_id}")
        keywords = list(db.keyword.find({"fk_group_id": group_id}))
        return group, keywords

    def _load_from_json(self, path):
        with open(path) as fh:
            payload = json.load(fh)
        return payload["group"], payload["keywords"]

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _as_datetime(value):
        """Mongo datetimes are naive; this project runs USE_TZ=True.

        Rankmax stores UTC (its crawls stamp ~03:00, which matches the nightly
        run in UTC), so they are attached to UTC rather than left naive for
        Django to assume a zone and warn about.
        """
        if value is None:
            return None
        if isinstance(value, str):
            value = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if not isinstance(value, datetime.datetime):
            return value
        if timezone.is_naive(value):
            return value.replace(tzinfo=datetime.timezone.utc)
        return value

    @classmethod
    def _as_date(cls, value):
        """Calendar date of a Mongo timestamp — the rank-history anchor."""
        dt = cls._as_datetime(value)
        return dt.date() if isinstance(dt, datetime.datetime) else dt

    @staticmethod
    def _host(url):
        return (url or "").replace("https://", "").replace("http://", "").strip("/").strip()

    def _country_for(self, keywords):
        codes = Counter((k.get("isocode") or "").lower() for k in keywords if k.get("isocode"))
        if not codes:
            return "India"
        return ISO_TO_COUNTRY.get(codes.most_common(1)[0][0], "India")

    # ------------------------------------------------------------------ mapping

    def _rank_rows(self, kw, history_days):
        """(date, position) pairs, oldest first.

        Rankmax's `rank` array is stored NEWEST FIRST: index 0 is the most
        recent crawl and index i is i days before it. Confirmed on 101 keywords
        across three projects — `ranknow` equals rank[0] in 101 cases and
        rank[-1] in only 55 — and by the engine's own day-over-day figures: a
        keyword with dayval=96/down reads [0, 4, ...] from the front (dropped
        out of the top 100 from #4 yesterday) and an unrelated 9-place move
        from the back.

        The span is created_date .. most recent crawl either way, so index 0
        is that final date and the array runs backwards from it:

            date(i) = created_date + (len - 1 - i) days

        Returns [] when the anchor is missing rather than guessing — a history
        row with an invented date is worse than no history row.
        """
        series = kw.get("rank") or []
        start = self._as_date(kw.get("created_date"))
        if not series or not start:
            return []
        last = len(series) - 1
        rows = [
            (start + datetime.timedelta(days=last - i), int(p or 0))
            for i, p in enumerate(series)
        ]
        rows.reverse()  # oldest first, so callers can slice the recent tail
        if history_days:
            rows = rows[-history_days:]
        return rows

    # ------------------------------------------------------------------ handle

    def handle(self, *args, **opts):
        group_id = opts["group_id"]
        dry = opts["dry_run"]

        if opts["from_json"]:
            group, kws = self._load_from_json(opts["from_json"])
        else:
            group, kws = self._load_from_mongo(group_id, opts["mongo_password"])

        name = group.get("group_name") or f"rankmax-{group_id}"
        url = group.get("domain_name") or ""
        host = self._host(url)
        if not host:
            raise CommandError(f"Group {group_id} has no domain_name")

        w = self.stdout.write
        w(self.style.MIGRATE_HEADING(f"\nRankmax group {group_id} — {name}"))
        w(f"  domain          {url}")
        w(f"  status          {group.get('domain_status')}")
        w(f"  keywords        {len(kws)}")

        # Pre-flight: an existing domain is a MERGE, which this command does not
        # do. Refuse rather than half-merge into a live project.
        existing = Domain.objects.filter(organisation_id=opts["org"]).filter(url=url).first()
        if not existing:
            for d in Domain.objects.filter(organisation_id=opts["org"]):
                if self._host(d.url).lower().removeprefix("www.") == host.lower().removeprefix("www."):
                    existing = d
                    break
        if existing:
            raise CommandError(
                f"'{existing.name}' (id={existing.id}) already tracks {existing.url} in org "
                f"{opts['org']}. This command only creates NEW projects — merging into an "
                f"existing one needs a separate decision about which side wins."
            )

        history_days = opts["history_days"]
        total_hist = 0
        spans = []
        for k in kws:
            rows = [] if opts["skip_history"] else self._rank_rows(k, history_days)
            total_hist += len(rows)
            if rows:
                spans.append((rows[0][0], rows[-1][0]))

        if spans:
            w(f"  history         {total_hist:,} rows, {min(s[0] for s in spans)} → {max(s[1] for s in spans)}")
        else:
            w("  history         none (skipped)")
        w(f"  country         {self._country_for(kws)}")
        w(f"  target org      {opts['org']}")
        no_anchor = [k for k in kws if (k.get('rank') and not k.get('created_date'))]
        if no_anchor:
            w(self.style.WARNING(
                f"  {len(no_anchor)} keyword(s) have history but no created_date — "
                f"their history will be SKIPPED (no trustworthy date anchor)."))

        w("")
        if dry:
            w(self.style.WARNING("DRY RUN — everything below is rolled back.\n"))

        try:
            with transaction.atomic():
                created = self._write(group, kws, opts, name, url)
                w(self.style.SUCCESS("Written:"))
                for label, n in created.items():
                    w(f"  {label:<22} {n:,}")
                if dry:
                    raise _Rollback()
        except _Rollback:
            w("")
            w(self.style.WARNING("DRY RUN complete — transaction rolled back, nothing persisted."))
            return

        w("")
        w(self.style.SUCCESS(f"Imported '{name}' into organisation {opts['org']}."))
        w("Keywords are NOT queued for crawling (auto_call_status='done') and will NOT "
          "generate GEO prompts (auto_generate_prompts=False).")

    # ------------------------------------------------------------------ write

    def _write(self, group, kws, opts, name, url):
        counts = Counter()

        domain = Domain.objects.create(
            name=name,
            url=url,
            organisation_id=opts["org"],
            country=self._country_for(kws),
            # Everything GEO stays untouched: no description, niches, tone,
            # business model, or competitor config. processing_status stays
            # INIT so no engine picks this domain up.
        )
        counts["domains"] = 1

        rank_rows = []
        for k in kws:
            text = (k.get("keyword") or "").strip()
            if not text:
                continue

            kw_obj, made = Keyword.objects.get_or_create(
                keyword=text[:255],
                domain=domain,
                defaults={
                    # False, not the model default True — see module docstring.
                    "auto_generate_prompts": False,
                    "source": "rankmax-import",
                },
            )
            counts["keywords"] += int(made)

            platform = (k.get("platform") or "desktop").lower()
            if platform not in PLATFORMS:
                platform = "desktop"

            series = k.get("rank") or []
            # rank[0] — the array is newest-first, so index 0 is today's
            # position. It agrees with `ranknow` on every keyword checked.
            rank_now = int(series[0] or 0) if series else int(k.get("ranknow") or 0)

            # Keyed on Rankmax's own tracking key: text + region + language +
            # device. One Keyword row can therefore carry several SeoKeywordRank
            # rows — the Arabic and English variants of a term on google.com.sa
            # are two tracked items with two rank histories, exactly as Rankmax
            # holds them.
            seo, made = SeoKeywordRank.objects.get_or_create(
                keyword=kw_obj,
                domain=domain,
                platform=platform,
                language_code=(k.get("language_code") or "en")[:8],
                region=(k.get("region") or "google.com")[:20],
                defaults={
                    "rank_now": rank_now,
                    "top_rank": k.get("top_rank") or None,
                    "rank_since_start": int(k.get("rank_sincestart") or 0),
                    "day_val": int(k.get("dayval") or 0),
                    "day_mark": (k.get("daymark") or "-")[:5],
                    "week_val": int(k.get("weekval") or 0),
                    "week_mark": (k.get("weekmark") or "-")[:5],
                    "half_month_val": int(k.get("halfmonthval") or 0),
                    "half_month_mark": (k.get("halfmonthmark") or "-")[:5],
                    "month_val": int(k.get("monthval") or 0),
                    "month_mark": (k.get("monthmark") or "-")[:5],
                    "status_from_start": (k.get("status_from_start") or "-")[:5],
                    "featured_snippet": bool(k.get("featured_snippet")),
                    "knowledge_panel": bool(k.get("knowledge_panel")),
                    "ads": bool(k.get("ads")),
                    "review": bool(k.get("review")),
                    "total_rating": str(k.get("total_rating") or "-")[:5],
                    "total_review": str(k.get("total_review") or "-")[:15],
                    "snippets_details": k.get("snippets_details") or {},
                    "keyword_snippet": k.get("keyword_snippet") or {},
                    "gsc_clicks": int(k.get("gsc_clicks") or 0),
                    "gsc_impressions": int(k.get("gsc_impressions") or 0),
                    "site_url": (k.get("site_url") or "")[:500],
                    "target_url": (k.get("target") or "")[:500],
                    "search_results": str(k.get("search_results") or "-")[:50],
                    "search_volume": k.get("search_volume") or None,
                    "isocode": (k.get("isocode") or "us")[:5],
                    "geo_target": (k.get("geo_target") or "")[:255],
                    "geo_target_uule": (k.get("geo_target_uule") or "")[:500],
                    "crawl_url": k.get("crawlurl") or "",
                    # 'done', not 'avail' — see module docstring.
                    "auto_call_status": "done",
                    "last_ranked_date": self._as_datetime(k.get("lastranked_date")),
                    "cannibalisation": k.get("cannibalisation") or [],
                    "tags": k.get("tags") or [],
                    "favour": int(k.get("favour") or 0),
                },
            )
            counts["seo_keyword_ranks"] += int(made)
            # Rankmax itself sometimes holds the identical tracked item twice
            # (same text, region, language and device). Those genuinely collapse
            # to one row — counted so the collapse is visible rather than a
            # silent discrepancy between the source count and what was written.
            counts["duplicate_source_rows"] += int(not made)

            if opts["skip_history"]:
                continue
            for day, position in self._rank_rows(k, opts["history_days"]):
                rank_rows.append(SeoRankHistory(
                    seo_keyword_rank=seo, snapshot_date=day, rank_position=position,
                ))

        if rank_rows:
            SeoRankHistory.objects.bulk_create(rank_rows, batch_size=2000, ignore_conflicts=True)
            counts["rank_history_rows"] = len(rank_rows)

        if not opts["skip_metrics"]:
            counts["daily_metric_rows"] = self._backfill_metrics(domain, rank_rows)

        return counts

    # ------------------------------------------------------------- daily metrics

    def _backfill_metrics(self, domain, rank_rows):
        """One SeoDomainDailyMetrics row per day, derived from the imported history.

        Without this the Keyword Rankings overview cards read zero: they come
        from SeoDomainDailyMetrics, which is written by the engine's daily
        snapshot job and knows nothing about a bulk import. The keyword table
        would show 27 rows above a row of zeroes.

        Computed from the history we just wrote rather than copied from
        Rankmax's own score_meter[] array, so the cards, the table and the
        chart are guaranteed to agree with each other. The weights come from
        score_service, which is what the nightly job uses — an imported day and
        a live day are scored identically.
        """
        from collections import defaultdict as _dd
        from seo_rankings.services.score_service import (
            score_allocation_calc, score_meter_calc, activity_calc,
        )

        # date -> {seo_keyword_rank_id: position}
        by_day = _dd(dict)
        platform_of = {}
        for row in rank_rows:
            by_day[row.snapshot_date][row.seo_keyword_rank_id] = row.rank_position
            platform_of[row.seo_keyword_rank_id] = row.seo_keyword_rank.platform

        metrics, prev = [], {}
        best = 0.0
        for day in sorted(by_day):
            positions = by_day[day]
            buckets = _dd(int)
            t1 = t3 = t10 = t50 = t100 = nr = 0
            desktop = mobile = 0
            improved = declined = same = 0

            for kid, rank in positions.items():
                buckets = score_allocation_calc(rank, buckets)
                if rank and rank > 0:
                    if rank == 1:
                        t1 += 1
                    if rank <= 3:
                        t3 += 1
                    if rank <= 10:
                        t10 += 1
                    if rank <= 50:
                        t50 += 1
                    if rank <= 100:
                        t100 += 1
                    if rank > 100:
                        nr += 1
                else:
                    nr += 1

                if platform_of.get(kid) == "mobile":
                    mobile += 1
                else:
                    desktop += 1

                # A lower number is a better position, so previous - current > 0
                # is an improvement. Rank 0 means "not ranked" and is not a
                # position, so transitions in or out of it are not movements.
                was = prev.get(kid)
                if was is None or was == 0 or rank == 0:
                    same += 1
                elif was > rank:
                    improved += 1
                elif was < rank:
                    declined += 1
                else:
                    same += 1

            total = len(positions)
            score = score_meter_calc(buckets, total)
            best = max(best, score)

            metrics.append(SeoDomainDailyMetrics(
                domain=domain, snapshot_date=day,
                score_meter=score, top_score=best,
                improved_count=improved, declined_count=declined, no_change_count=same,
                activity_level=activity_calc(improved, declined, total),
                top_1_count=t1, top_3_count=t3, top_10_count=t10,
                top_50_count=t50, top_100_count=t100, not_ranked_count=nr,
                desktop_count=desktop, mobile_count=mobile,
                total_keywords=total,
            ))
            prev = positions

        SeoDomainDailyMetrics.objects.bulk_create(metrics, batch_size=500, ignore_conflicts=True)
        return len(metrics)


class _Rollback(Exception):
    """Aborts the transaction at the end of a dry run."""
