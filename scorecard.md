# TSM 5-day call: live scorecard

**Latest call** (close of 2026-11-18, TSM $362.62, result due about 2026-11-25):

- Logistic regression: **UP** (53% chance of UP)
- Gradient boosting: **UP** (71% chance of UP)

## Accuracy so far

| Strategy | Hits / scored | Accuracy | 95% range |
|---|---|---|---|
| Always up | 9 / 27 | 33% | 9% to 71% |
| Logistic regression | 11 / 27 | 41% | 13% to 77% |
| Gradient boosting | 13 / 27 | 48% | 17% to 81% |

The 95% range shows how much of the accuracy could be luck. Daily calls overlap (each covers 5 trading days), so the range treats N calls as about N/5 separate weeks.

## Last 10 calls

| Close of | Logistic | Boosting | Actual 5-day move |
|---|---|---|---|
| 2026-11-18 | UP (53%) | UP (71%) | pending |
| 2026-11-17 | UP (59%) | UP (74%) | pending |
| 2026-11-16 | UP (61%) | UP (61%) | pending |
| 2026-11-13 | UP (54%) | UP (61%) | pending |
| 2026-11-12 | UP (52%) | UP (59%) | pending |
| 2026-11-11 | DOWN (45%) | DOWN (42%) | DOWN (-12.3%) |
| 2026-11-10 | DOWN (45%) | DOWN (44%) | DOWN (-9.3%) |
| 2026-11-09 | DOWN (44%) | DOWN (41%) | DOWN (-3.9%) |
| 2026-11-06 | DOWN (43%) | UP (74%) | UP (+6.2%) |
| 2026-11-05 | UP (65%) | UP (86%) | UP (+14.8%) |

![Running accuracy](scorecard.png)
