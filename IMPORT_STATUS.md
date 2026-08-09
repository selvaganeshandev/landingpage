# Rankmax → PromptMaxx import status

Source: Rankmax MongoDB `mystery_dev_2024`, the 49 projects owned by
`@pivotroots.com` accounts. Target: PromptMaxx organisation 1.

Last updated: 2026-08-09 — **complete**.

## Summary

| | Projects | Rankmax keywords |
|---|---:|---:|
| Imported | 47 | 20,786 |
| Skipped (identical duplicates) | 2 | 200 |
| **Total** | **49** | **20,986** |

Organisation 1 now holds **66 domains**, **20,646 tracked keywords** and
**6,098,691 rank-history rows**, against 41 domains and 230,968 rows before the migration.

Rankmax counts source documents. PromptMaxx counts *tracked items*: the same
keyword on two devices or in two languages is two rows, and a keyword entered
twice on the same device collapses to one. The two figures therefore differ on
some projects, and that is expected rather than loss.

## Imported

Grouped by the PromptMaxx project the data landed in, so pairs that merged
into one project appear together.

| PromptMaxx | Project | Rankmax group(s) | Rankmax kw | Tracked | History |
|---:|---|---|---:|---:|---:|
| 156 | Thomas Cook Forex | 6527 + 6804 | 2,387 | 2,349 | 1,606,067 |
| 150 | New India Assurance | 6675 | 902 | 902 | 464,530 |
| 154 | CoinDCX | 6837 | 3,507 | 3,507 | 459,417 |
| 148 | Bharatvedica | 6725 | 796 | 796 | 322,380 |
| 157 | Kotak Bank | 6842 + 6833 | 2,429 | 2,428 | 296,875 |
| 146 | HH Khar | 6683 | 499 | 499 | 246,506 |
| 14 | Voltas | 6766 | 735 | 679 | 234,334 |
| 54 | Racold | 6511 | 324 | 312 | 230,970 |
| 61 | Hinduja Hospital | 6709 | 500 | 500 | 223,000 |
| 66 | Kotak811 | 6821 | 1,189 | 1,189 | 198,563 |
| 62 | HPV - MSD | 6700 | 261 | 261 | 121,887 |
| 74 | Shriram Wealth | 6739 | 282 | 282 | 95,942 |
| 137 | Steve Madden | 6472 | 158 | 158 | 93,536 |
| 75 | MMTC-PAMP | 6777 | 378 | 378 | 92,658 |
| 132 | Crocs UAE | 6621 | 143 | 143 | 90,948 |
| 133 | Crocs Kuwait | 6626 | 143 | 143 | 90,948 |
| 130 | Crocs KSA | 6622 | 142 | 142 | 90,312 |
| 131 | Crocs Qatar | 6623 | 142 | 142 | 90,312 |
| 159 | Kotak811 ZB Bank In | 6810 | 506 | 506 | 88,550 |
| 129 | Crocs Oman | 6624 | 139 | 139 | 88,404 |
| 125 | Crocs Bharain | 6625 | 137 | 137 | 87,132 |
| 140 | Nysaa | 6473 | 200 | 120 | 84,540 |
| 135 | Steve Madden KSA | 6627 | 132 | 132 | 70,540 |
| 15 | Grown Brilliance | 6703 | 151 | 151 | 69,092 |
| 144 | Beyon | 6815 | 344 | 344 | 59,168 |
| 11 | Edelweisslife India | 6801 | 289 | 275 | 55,550 |
| 142 | Vector Consulting Group | 6769 | 256 | 256 | 46,594 |
| 68 | Gargash Insurance | 6551 | 100 | 69 | 38,324 |
| 40 | CanaraHSBCLife Insurance | 6854 | 912 | 912 | 38,304 |
| 155 | BitOasis | 6764 + 6765 | 100 | 100 | 34,600 |
| 65 | Artiscents | 6767 | 100 | 100 | 34,200 |
| 120 | Woodland | 6530 | 42 | 42 | 30,828 |
| 9 | Menolabs | 6788 | 105 | 105 | 27,930 |
| 118 | Crocs | 6589 | 41 | 39 | 26,382 |
| 117 | DXBBQ | 6469 | 33 | 33 | 26,268 |
| 26 | Fnp | 6834 | 295 | 295 | 20,172 |
| 38 | PivotRoots | 6802 + 6808 | 89 | 89 | 16,135 |
| 160 | Shriram Wealth (Mobile) | 6736 | 34 | 34 | 12,614 |
| 152 | Turtlemintpro | 6865 | 1,279 | 1,279 | 12,454 |
| 116 | YCH | 6720 | 27 | 27 | 11,475 |
| 87 | Paradise Kerala | 6846 | 155 | 155 | 10,695 |
| 55 | Get Zype | 6863 | 325 | 325 | 4,225 |
| 123 | Carrier India | 6864 | 78 | 78 | 936 |

## Skipped

| Rankmax group | Project | Domain | Keywords | Why |
|---:|---|---|---:|---|
| 6794 | Artiscents | `www.artiscents.com` | 100 | Byte-identical copy of group 6767, already imported as project 65 |
| 6793 | Artiscents | `www.artiscents.com` | 100 | Byte-identical copy of group 6767, already imported as project 65 |

## Notes on specific projects

**Kotak811** — Rankmax holds two projects on one domain and PromptMaxx now does
too (ids 66 and 159). 503 of the 506 keywords in `Kotak811 ZB Bank In` are the
same terms, on the same device, as in `Kotak811BankIn`, so those keywords are
tracked and billed twice. This mirrors Rankmax deliberately.

**Shriram Wealth** — also two projects (ids 74 and 160), split by device. The
mobile one was renamed `Shriram Wealth (Mobile)`; both Rankmax entries are
called `Shriram Wealth`, which would be indistinguishable in any list.

**canara hsbc (id 40)** — imported with `--replace-existing`. PromptMaxx held
1,765 tracked keywords and 161,945 history rows; all were deleted and replaced
with Rankmax's 912 keywords and 38,304 rows. 853 keywords that existed only in
PromptMaxx are gone, as instructed. This is the only project where the replace
removed more than it added.

**Nysaa (id 140)** — 200 source documents became 120 tracked keywords: 80 terms
had been added to the project twice on the same device.

**Thomas Cook (id 156)** and **Kotak Bank (id 157)** — each pair merged into one
project. 34 and 1 colliding keywords respectively were skipped with
`--skip-conflicts`; the existing history was kept for those.

## How the import works

```
manage.py import_rankmax_project --group-id <id>
    [--merge-into <domain_id>]   attach to an existing project
    [--replace-existing]         delete the target's SEO data first
    [--skip-conflicts]           import only the keywords that do not collide
    [--new-project]              second project on a domain already tracked
    [--name <text>]              override the Rankmax project name
    [--dry-run]                  write, report, roll back
```

- **History dates.** Rankmax stores `rank` as a bare int array, newest first,
  with no dates: `date(i) = created_date + (len - 1 - i)` days. Verified across
  147 keywords — every one implies the same final date.
- **Current position** is `rank[0]`, not `ranknow`, which drifts on some keywords.
- **Numeric fields** arrive as strings and sometimes as the sentinel `'init'`;
  anything non-numeric becomes the field default rather than failing the import.
- **Cost controls.** Every imported keyword gets `auto_generate_prompts = False`
  and `auto_call_status = 'done'`, so none of the 20,000+ enters GEO prompt
  generation or the daily SERP crawl queue. Both differ from the model defaults.
- **Verification.** Every project was checked against live Rankmax on current
  rank, the full position series element by element, and both date anchors.

## Related follow-ups, not part of the import

- No usable database backup: the only dump is a hand-taken one from 2026-07-20,
  and `archive_mode = off`, so there is no point-in-time recovery.
- `snapshot_keyword_rankings` has failed on every scheduled run since 2026-04-06
  with a `ModuleNotFoundError`.
- The PromptMaxx Score renders `1.54` as a bare `2`; it needs a decimal and a
  `/100` to read as a score rather than a rank.
