# Rankmax → PromptMaxx import status

Source: Rankmax MongoDB `mystery_dev_2024`, the 49 projects owned by
`@pivotroots.com` accounts. Target: PromptMaxx organisation 1.

Last updated: 2026-08-10

## Summary

| Status | Projects | Keywords |
|---|---:|---:|
| Imported | 34 | 11,997 |
| In progress | 1 | 2,336 |
| On hold — awaiting client | 4 | 2,011 |
| Needs a decision | 10 | 4,642 |
| **Total** | **49** | **20,986** |

Rankmax keyword counts are source document counts. PromptMaxx stores one row
per *tracked item* — the same keyword on two devices or in two languages is
two rows, and a keyword entered twice on the same device collapses to one —
so the two figures legitimately differ on some projects.

## Imported

| Rankmax group | Project | Domain | Keywords | PromptMaxx | Tracked | History |
|---:|---|---|---:|---:|---:|---:|
| 6837 | CoinDCX | `coindcx.com` | 3,507 | id 154 | 3,507 | 459,417 |
| 6865 | Turtlemintpro | `turtlemintpro.com` | 1,279 | id 152 | 1,279 | 12,454 |
| 6675 | New India Assurance | `newindia.co.in` | 902 | id 150 | 902 | 464,530 |
| 6725 | Bharatvedica | `bharatvedica.com` | 796 | id 148 | 796 | 322,380 |
| 6766 | Voltas | `voltas.com` | 735 | id 14 | 679 | 234,334 |
| 6683 | HH Khar | `khar.hindujahospital.com` | 499 | id 146 | 499 | 246,506 |
| 6777 | MMTC PAMP | `mmtcpamp.com` | 378 | id 75 | 378 | 92,658 |
| 6815 | Beyon | `beyon.co.in` | 344 | id 144 | 344 | 59,168 |
| 6863 | Zype | `getzype.com` | 325 | id 55 | 325 | 4,225 |
| 6511 | Racold | `racold.com` | 324 | id 54 | 312 | 230,970 |
| 6801 | Edelweiss Life | `edelweisslife.in` | 289 | id 11 | 275 | 55,550 |
| 6700 | MSD HPV | `letsfighthpv.com` | 261 | id 62 | 261 | 121,887 |
| 6769 | Vector Consulting Group | `vectorconsulting.in` | 256 | id 142 | 256 | 46,594 |
| 6473 | Nysaa | `nysaa.com` | 200 | id 140 | 120 | 84,540 |
| 6472 | Steve Madden | `stevemadden.me` | 158 | id 137 | 158 | 93,536 |
| 6703 | Grown Brilliance | `grownbrilliance.com` | 151 | id 15 | 151 | 69,092 |
| 6621 | Crocs UAE | `en-ae.crocsgulf.com` | 143 | id 132 | 143 | 90,948 |
| 6626 | Crocs Kuwait | `en-kw.crocsgulf.com` | 143 | id 133 | 143 | 90,948 |
| 6622 | Crocs KSA | `en-sa.crocsgulf.com` | 142 | id 130 | 142 | 90,312 |
| 6623 | Crocs Qatar | `en-qa.crocsgulf.com` | 142 | id 131 | 142 | 90,312 |
| 6624 | Crocs Oman | `en-om.crocsgulf.com` | 139 | id 129 | 139 | 88,404 |
| 6625 | Crocs Bharain | `en-bh.crocsgulf.com` | 137 | id 125 | 137 | 87,132 |
| 6627 | Steve Madden KSA | `stevemadden.sa` | 132 | id 135 | 132 | 70,540 |
| 6788 | MenoLabs | `menolabs.com` | 105 | id 9 | 105 | 27,930 |
| 6551 | Gargash Insurance | `gargashinsurance.com` | 100 | id 68 | 69 | 38,324 |
| 6764 | BitOasis | `bitoasis.net` | 80 | id 155 | 100 | 34,600 |
| 6864 | Carrier India | `carrier.com` | 78 | id 123 | 78 | 936 |
| 6802 | PivotRoots | `pivotroots.com` | 54 | id 38 | 89 | 16,135 |
| 6530 | Woodland | `woodlandworldwide.com` | 42 | id 120 | 42 | 30,828 |
| 6589 | Crocs | `ar-sa.crocsgulf.com` | 41 | id 118 | 39 | 26,382 |
| 6808 | PivotRoots UAE | `pivotroots.com` | 35 | id 38 | 89 | 16,135 |
| 6469 | DXBBQ | `dxbbq.ae` | 33 | id 117 | 33 | 26,268 |
| 6720 | YCH | `ych.com` | 27 | id 116 | 27 | 11,475 |
| 6765 | BitOasis Arabic | `bitoasis.net` | 20 | id 155 | 100 | 34,600 |

## In progress

- **Thomas Cook Forex** (group 6527, `thomascook.in`) — 2,336 keywords, ~1.6M history points.
  Largest project in the migration; creates a new PromptMaxx project.

## On hold — awaiting client confirmation

Both are cases where two Rankmax projects share a URL **and** every tracking
dimension, so PromptMaxx cannot hold them as separate projects
(`Domain.unique_together = [url, organisation]`) and cannot merge them without
one keyword carrying two rank histories.

| Rankmax group | Project | Domain | Keywords | PromptMaxx target |
|---:|---|---|---:|---|
| 6821 | Kotak811BankIn | `kotak811.bank.in` | 1,189 | id 66 (0 tracked) |
| 6810 | Kotak811 ZB Bank In | `kotak811.bank.in` | 506 | id 66 (0 tracked) |
| 6739 | Shriram Wealth | `shriramwealth.in` | 282 | id 74 (0 tracked) |
| 6736 | Shriram Wealth | `shriramwealth.in` | 34 | id 74 (0 tracked) |

**Kotak811** — 503 of the 506 keywords in `Kotak811 ZB Bank In` are also in
`Kotak811BankIn`, on the same platform, language and region. The larger project
was created eight days later and is a near-superset.

**Shriram Wealth** — the two are a genuine desktop/mobile split (282 desktop,
34 mobile, all 34 shared). Merging them into one PromptMaxx project would
preserve the split on the keyword rows; keeping them as two projects is what
the schema forbids.

## Needs a decision

| Rankmax group | Project | Domain | Keywords | Conflict |
|---:|---|---|---:|---|
| 6842 | Kotak Bank | `kotak.bank.in` | 1,792 | pair with 6833; only 1 colliding keyword between them |
| 6854 | canara hsbc | `canarahsbclife.com` | 912 | PromptMaxx already tracks 1,765 keywords — more than Rankmax has |
| 6833 | kotak mobile ranking | `kotak.bank.in` | 637 | pair with 6842; mostly desktop despite the name |
| 6709 | Hinduja Mahim | `hindujahospital.com` | 500 | PromptMaxx id 61 already tracks 13 keywords |
| 6834 | FNP | `fnp.com` | 295 | PromptMaxx already tracks 290 keywords |
| 6846 | Paradise Holidays | `paradise-kerala.com` | 155 | PromptMaxx already tracks 155 keywords |
| 6767 | Artiscents | `artiscents.com` | 100 | three identical 100-keyword projects; PM id 65 tracks 5 (backlinks demo) |
| 6794 | Artiscents | `artiscents.com` | 100 | duplicate of 6767 |
| 6793 | Artiscents | `artiscents.com` | 100 | duplicate of 6767 |
| 6804 | Thomas Cook Mobile | `thomascook.in` | 51 | 34 of its 51 keywords collide with Thomas Cook Forex |

## How the import works

`manage.py import_rankmax_project --group-id <id> [--merge-into <domain_id>]`

- **Rank history dates.** Rankmax stores `rank` as a bare int array, newest
  first, with no dates. `date(i) = created_date + (len - 1 - i)` days.
  Verified across 147 keywords: every one implies the same final date.
- **Current position** is `rank[0]`, not `ranknow`, which drifts on some
  keywords.
- **Cost controls.** Imported keywords get `auto_generate_prompts = False` so
  they never enter GEO prompt generation, and `auto_call_status = 'done'` so
  they never enter the daily SERP crawl queue. Both differ from the model
  defaults and are the reason ~12,000 imported keywords cost nothing to hold.
- **Merging** is permitted only where no incoming keyword collides with one
  the target already tracks, compared on (keyword, platform, language, region).
- **Verification.** Every import is checked against live Rankmax on current
  rank, the full position series element by element, and both date anchors.
