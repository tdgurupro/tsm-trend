# TSM 5-day call: live scorecard

**Latest call** (close of 2026-11-06, TSM $375.44, result due about 2026-11-13):

- Logistic regression: **DOWN** (43% chance of UP)
- Gradient boosting: **UP** (74% chance of UP)

## Accuracy so far

| Strategy | Hits / scored | Accuracy | 95% range |
|---|---|---|---|
| Always up | 6 / 19 | 32% | 7% to 75% |
| Logistic regression | 6 / 19 | 32% | 7% to 75% |
| Gradient boosting | 7 / 19 | 37% | 9% to 78% |

The 95% range shows how much of the accuracy could be luck. Daily calls overlap (each covers 5 trading days), so the range treats N calls as about N/5 separate weeks.

## Last 10 calls

| Close of | Logistic | Boosting | Actual 5-day move |
|---|---|---|---|
| 2026-11-06 | DOWN (43%) | UP (74%) | pending |
| 2026-11-05 | UP (65%) | UP (86%) | pending |
| 2026-11-04 | UP (55%) | UP (78%) | pending |
| 2026-11-03 | UP (55%) | UP (73%) | pending |
| 2026-11-02 | UP (57%) | UP (80%) | pending |
| 2026-10-30 | UP (63%) | UP (67%) | DOWN (-7.6%) |
| 2026-10-29 | UP (61%) | UP (57%) | DOWN (-18.2%) |
| 2026-10-28 | UP (58%) | UP (64%) | DOWN (-10.0%) |
| 2026-10-27 | UP (54%) | UP (54%) | DOWN (-7.3%) |
| 2026-10-26 | UP (54%) | UP (54%) | DOWN (-6.1%) |

![Running accuracy](scorecard.png)
