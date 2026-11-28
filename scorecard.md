# TSM 5-day call: live scorecard

**Latest call** (close of 2026-11-27, TSM $353.34, result due about 2026-12-04):

- Logistic regression: **DOWN** (31% chance of UP)
- Gradient boosting: **UP** (67% chance of UP)

## Accuracy so far

| Strategy | Hits / scored | Accuracy | 95% range |
|---|---|---|---|
| Always up | 10 / 33 | 30% | 9% to 66% |
| Logistic regression | 12 / 33 | 36% | 12% to 71% |
| Gradient boosting | 14 / 33 | 42% | 15% to 75% |

The 95% range shows how much of the accuracy could be luck. Daily calls overlap (each covers 5 trading days), so the range treats N calls as about N/5 separate weeks.

## Last 10 calls

| Close of | Logistic | Boosting | Actual 5-day move |
|---|---|---|---|
| 2026-11-27 | DOWN (31%) | UP (67%) | pending |
| 2026-11-25 | DOWN (40%) | UP (68%) | pending |
| 2026-11-24 | DOWN (42%) | UP (73%) | pending |
| 2026-11-23 | DOWN (31%) | UP (51%) | pending |
| 2026-11-20 | UP (69%) | UP (93%) | pending |
| 2026-11-19 | UP (61%) | UP (73%) | UP (+0.4%) |
| 2026-11-18 | UP (53%) | UP (71%) | DOWN (-5.6%) |
| 2026-11-17 | UP (59%) | UP (74%) | DOWN (-2.9%) |
| 2026-11-16 | UP (61%) | UP (61%) | DOWN (-2.6%) |
| 2026-11-13 | UP (54%) | UP (61%) | DOWN (-20.1%) |

![Running accuracy](scorecard.png)
