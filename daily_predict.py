"""
Daily runner for the TSM 5-day call.

Run once per trading day after the New York close (the GitHub robot does this
at 22:30 UTC = 06:30 Taipei, Monday to Friday). Each run:

  1. downloads fresh prices and saves a snapshot to data/prices.csv
     (the class notebook's Plan B if Yahoo Finance is down in class),
  2. scores every earlier call whose 5 trading days have now passed,
  3. trains both models on all history and logs today's call in
     predictions_log.csv BEFORE the outcome can be known,
  4. rewrites scorecard.md and scorecard.png for the weekly class update.

Try it without internet:  python daily_predict.py --source synthetic --out demo
"""
import argparse
import os

import matplotlib

matplotlib.use("Agg")

import tsm_pipeline as tp


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", choices=["yahoo", "synthetic"], default="yahoo",
                        help="'synthetic' uses a fake random-walk stock (for testing only)")
    parser.add_argument("--out", default=".", help="folder for the log, snapshot and scorecard")
    args = parser.parse_args()

    panel = tp.download_prices() if args.source == "yahoo" else tp.make_synthetic_panel()
    os.makedirs(os.path.join(args.out, "data"), exist_ok=True)
    panel.to_csv(os.path.join(args.out, "data", "prices.csv"), float_format="%.6f")

    log_path = os.path.join(args.out, "predictions_log.csv")
    log, new_row = tp.update_log(tp.load_log(log_path), panel)
    log.to_csv(log_path, index=False)
    tp.write_scorecard(log, args.out)

    if new_row is None:
        print(f"Close of {panel.index[-1]:%Y-%m-%d} was already logged (holiday or re-run). Scores refreshed.")
    else:
        print(f"Logged call for the close of {new_row['as_of_date']} (TSM ${new_row['tsm_close']:,.2f}):")
        for name, key in tp.MODEL_KEYS.items():
            print(f"  {name:<20} {new_row[f'call_{key}']:<4}  "
                  f"({new_row[f'prob_up_{key}']:.0%} chance of UP)")
    print(tp.scorecard_table(log).to_string(float_format=lambda v: f"{v:.1%}"))


if __name__ == "__main__":
    main()
