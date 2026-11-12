# TSM 5-day call: live scorecard

**Latest call** (close of 2026-11-11, TSM $413.35, result due about 2026-11-18):

- Logistic regression: **DOWN** (45% chance of UP)
- Gradient boosting: **DOWN** (42% chance of UP)

## Accuracy so far

| Strategy | Hits / scored | Accuracy | 95% range |
|---|---|---|---|
| Always up | 7 / 22 | 32% | 7% to 73% |
| Logistic regression | 7 / 22 | 32% | 7% to 73% |
| Gradient boosting | 8 / 22 | 36% | 9% to 76% |

The 95% range shows how much of the accuracy could be luck. Daily calls overlap (each covers 5 trading days), so the range treats N calls as about N/5 separate weeks.

## Last 10 calls

| Close of | Logistic | Boosting | Actual 5-day move |
|---|---|---|---|
| 2026-11-11 | DOWN (45%) | DOWN (42%) | pending |
| 2026-11-10 | DOWN (45%) | DOWN (44%) | pending |
| 2026-11-09 | DOWN (44%) | DOWN (41%) | pending |
| 2026-11-06 | DOWN (43%) | UP (74%) | pending |
| 2026-11-05 | UP (65%) | UP (86%) | pending |
| 2026-11-04 | UP (55%) | UP (78%) | UP (+4.4%) |
| 2026-11-03 | UP (55%) | UP (73%) | DOWN (-2.1%) |
| 2026-11-02 | UP (57%) | UP (80%) | DOWN (-2.5%) |
| 2026-10-30 | UP (63%) | UP (67%) | DOWN (-7.6%) |
| 2026-10-29 | UP (61%) | UP (57%) | DOWN (-18.2%) |

![Running accuracy](scorecard.png)
