#!/usr/bin/env python3
"""Settles paper trades against Kalshi's official resolutions and scores
calibration. The honest metric is brier_delta = Brier(market) - Brier(mine):
positive means the model's probability beat the market's price.

Read-only except for updating the paper log with settlement outcomes.
Never places orders.
"""
import datetime
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "core"))
from kalshi_client import kalshi_get  # noqa: E402


def load_settings():
    with open(os.path.join(BASE, "config", "settings.json")) as f:
        cfg = json.load(f)
    # Optional operator overrides (gitignored). Keys in the local file
    # replace the committed defaults; the nested "real" dict merges key-wise.
    local_path = os.path.join(BASE, "config", "settings.local.json")
    if os.path.exists(local_path):
        with open(local_path) as f:
            local = json.load(f)
        real = local.pop("real", None)
        cfg.update(local)
        if real:
            cfg.setdefault("real", {}).update(real)
    return cfg


def load_log(path):
    sigs = []
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        sigs.append(json.loads(line))
                    except json.JSONDecodeError:
                        print("WARN: skipping bad log line", file=sys.stderr)
    return sigs


def save_log(path, sigs):
    with open(path, "w") as f:
        for s in sigs:
            f.write(json.dumps(s) + "\n")


def settle(sigs):
    changed = 0
    for s in sigs:
        if s.get("settled") or not s.get("signal"):
            continue
        try:
            result = (kalshi_get(f"/trade-api/v2/markets/{s['ticker']}"
                                 ).get("market") or {}).get("result")
        except Exception as e:
            print(f"settle skip {s['ticker']}: {e}", file=sys.stderr)
            continue
        if result not in ("yes", "no"):
            continue
        s["settled"] = True
        s["outcome_yes"] = 1 if result == "yes" else 0
        s["settled_at"] = datetime.datetime.now(
            datetime.timezone.utc).isoformat()
        changed += 1
    return changed


def yes_price(s):
    return s["signal_price"] if s["side"] == "YES" else 1 - s["signal_price"]


def sim_pnl(s):
    n = s.get("contracts", 0)
    cost = n * (s.get("signal_price") or 0) + s.get("est_fee", 0.0)
    if s["side"] == "YES":
        payout = n * s["outcome_yes"]
    else:
        payout = n * (1 - s["outcome_yes"])
    return payout - cost, cost


def bucket(min_left):
    if min_left is None:
        return "?"
    if min_left < 5:
        return "<5m"
    if min_left < 10:
        return "5-10m"
    return "10m+"


def report(sigs):
    settled = [s for s in sigs if s.get("settled")]
    pending = [s for s in sigs if s.get("signal") and not s.get("settled")]
    # Calibration hygiene: entries with no market price at scan time
    # (side="none", or signal_price null because the window was already
    # finalized) are scan artifacts, not real signals. Exclude from scoring.
    cal = [s for s in settled
           if s.get("side") != "none" and s.get("signal_price") is not None]
    excluded = len(settled) - len(cal)
    lines = [f"HUNCHO TRADER REPORT ({len(sigs)} markets logged, "
             f"{len(settled)} signals settled, {len(pending)} awaiting)"]
    if excluded:
        lines.append(f"Excluding {excluded} scan artifact(s) with no market "
                     f"price at scan time from calibration.")
    if not cal:
        lines.append("No settled signals yet. brier_delta needs settled data.")
        return "\n".join(lines)
    tot_d = tot_pnl = tot_cost = 0.0
    wins = placed_n = placed_wins = 0
    placed_d = unplaced_d = 0.0
    unplaced_n = 0
    cats = {}
    for s in cal:
        p, mkt, o = s["my_prob_yes"], yes_price(s), s["outcome_yes"]
        d = (mkt - o) ** 2 - (p - o) ** 2
        tot_d += d
        pnl, cost = sim_pnl(s)
        tot_pnl += pnl
        tot_cost += cost
        if (s["side"] == "YES") == (o == 1):
            wins += 1
        if s.get("placed"):
            placed_n += 1
            placed_d += d
            placed_wins += pnl > 0
        else:
            unplaced_n += 1
            unplaced_d += d
        key = (s.get("asset", "?"), s.get("side", "?"),
               bucket(s.get("min_left")))
        c = cats.setdefault(key, {"n": 0, "d": 0.0, "pnl": 0.0})
        c["n"] += 1
        c["d"] += d
        c["pnl"] += pnl
    n = len(cal)
    verdict = "BEATING" if tot_d > 0 else "TRAILING"
    lines.append(f"Avg brier_delta: {tot_d/n:+.4f} per signal ({verdict} the market)")
    if placed_n:
        lines.append(f"  placed signals: n={placed_n} "
                     f"avg_d={placed_d/placed_n:+.4f}")
    if unplaced_n:
        lines.append(f"  not placed (incl. stale): n={unplaced_n} "
                     f"avg_d={unplaced_d/unplaced_n:+.4f}")
    lines.append(f"Signal hit rate: {wins}/{n} = {wins/n:.1%}")
    lines.append(f"Simulated P&L (as if all placed): ${tot_pnl:+.2f} "
                 f"on ${tot_cost:.2f} risked")
    lines.append(f"Real placed: {placed_n} trades, {placed_wins} winners")
    lines.append("")
    lines.append("By category (asset, side, time-left):")
    for key in sorted(cats):
        c = cats[key]
        lines.append(f"  {key[0]:4s} {key[1]:3s} {key[2]:6s}  "
                     f"n={c['n']:3d}  avg_d={c['d']/c['n']:+.4f}  "
                     f"pnl=${c['pnl']:+.2f}")
    lines.append("")
    lines.append("Honest metric is brier_delta, not P&L. Categories need 10+ "
                 "settled signals before earning real money (see REAL.md).")
    return "\n".join(lines)


def main():
    cfg = load_settings()
    log_path = os.path.join(BASE, cfg.get("paper_log", "paper/paper_log.jsonl"))
    sigs = load_log(log_path)
    changed = settle(sigs)
    if changed:
        save_log(log_path, sigs)
    print(f"Settled {changed} new signal(s).")
    print(report(sigs))


if __name__ == "__main__":
    main()
