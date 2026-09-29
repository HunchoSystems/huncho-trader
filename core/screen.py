#!/usr/bin/env python3
"""Paper screener: scans Kalshi 15M crypto windows, estimates fair value with the
v1 vol model, paper-logs EVERY evaluated market, and prints signals that clear
the edge bar.

Paper only. Never places orders. The log is the training data: be honest.
"""
import datetime
import json
import math
import os
import re
import sys
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "core"))
from kalshi_client import kalshi_get  # noqa: E402


def load_settings():
    path = os.path.join(BASE, "config", "settings.json")
    with open(path) as f:
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


def norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def spot_price(asset):
    url = f"https://api.coinbase.com/v2/prices/{asset}-USD/spot"
    req = urllib.request.Request(url, headers={"User-Agent": "huncho-trader"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return float(json.loads(r.read().decode())["data"]["amount"])


def taker_fee(contracts, price):
    # Kalshi taker fee rounds up per contract: ceil(n * 0.07 * p * (1-p))
    return math.ceil(contracts * 0.07 * price * (1 - price) * 100) / 100


def fair_yes_prob(spot, strike, minutes_left, vol_annual):
    """v1 model: lognormal, no drift. P(expiry spot >= strike)."""
    if minutes_left <= 0 or spot <= 0 or strike <= 0:
        return None
    tau = minutes_left / 525600.0
    iv = vol_annual * math.sqrt(tau)
    if iv <= 0:
        return 1.0 if spot >= strike else 0.0
    return norm_cdf(math.log(spot / strike) / iv)


def strike_of(market):
    s = market.get("strike") or market.get("floor_strike")
    if s:
        return float(s)
    # fallback: parse "$2,688.15 or above" style subtitles
    txt = (market.get("yes_sub_title") or "") + " " + (market.get("title") or "")
    nums = re.findall(r"\$?([\d,]+\.\d+)", txt)
    return float(nums[0].replace(",", "")) if nums else None


def size_contracts(ask, max_cost):
    n = max(1, int(max_cost // ask)) if ask > 0 else 0
    while n > 1 and n * ask + taker_fee(n, ask) > max_cost:
        n -= 1
    return n


def main():
    cfg = load_settings()
    edge_bar = cfg.get("edge_bar_cents", 8) / 100.0
    max_cost = cfg.get("max_cost_per_trade", 2.0)
    min_minutes = cfg.get("min_minutes_left", 3)
    vols = cfg.get("vol_annual", {})
    log_path = os.path.join(BASE, cfg.get("paper_log", "paper/paper_log.jsonl"))
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    now = datetime.datetime.now(datetime.timezone.utc)
    ts = now.isoformat()
    evaluated, signals = 0, []

    for series in cfg.get("series", ["KXETH15M"]):
        asset = "ETH" if "ETH" in series else "BTC" if "BTC" in series else None
        if not asset:
            continue
        try:
            spot = spot_price(asset)
        except Exception as e:
            print(f"{series}: spot fetch failed: {e}")
            continue
        vol = vols.get(asset, 0.6)
        try:
            events = kalshi_get(
                f"/trade-api/v2/events?series_ticker={series}&status=open&limit=5"
            ).get("events", [])
        except Exception as e:
            print(f"{series}: events fetch failed: {e}")
            continue
        for ev in events:
            try:
                markets = kalshi_get(
                    f"/trade-api/v2/events/{ev['event_ticker']}"
                ).get("markets", [])
            except Exception as e:
                print(f"{ev.get('event_ticker')}: markets fetch failed: {e}")
                continue
            for m in markets:
                ticker = m.get("ticker", "")
                strike = strike_of(m)
                if not strike:
                    continue
                try:
                    close = datetime.datetime.fromisoformat(
                        m.get("close_time", "").replace("Z", "+00:00"))
                    minutes_left = (close - now).total_seconds() / 60.0
                except Exception:
                    continue
                if minutes_left < min_minutes:
                    continue
                yes_bid = (m.get("yes_bid") or 0) / 100.0
                yes_ask = (m.get("yes_ask") or 100) / 100.0
                no_ask = (m.get("no_ask") or 100) / 100.0
                fair = fair_yes_prob(spot, strike, minutes_left, vol)
                if fair is None:
                    continue
                yes_edge = fair - yes_ask
                no_edge = (1 - fair) - no_ask
                if yes_edge >= no_edge:
                    side, edge, ask = "YES", yes_edge, yes_ask
                else:
                    side, edge, ask = "NO", no_edge, no_ask
                evaluated += 1
                is_signal = edge >= edge_bar
                contracts = size_contracts(ask, max_cost) if is_signal else 0
                fee = taker_fee(contracts, ask) if is_signal else 0.0
                entry = {
                    "ts": ts, "ticker": ticker, "asset": asset, "side": side,
                    "my_prob_yes": round(fair, 4),
                    "market_yes_bid": round(yes_bid, 3),
                    "market_yes_ask": round(yes_ask, 3),
                    "signal_price": round(ask, 3) if is_signal else None,
                    "contracts": contracts, "est_fee": fee,
                    "edge_c": round(edge * 100, 1),
                    "min_left": round(minutes_left, 1),
                    "spot": round(spot, 2), "strike": strike,
                    "signal": is_signal, "placed": False,
                    "model": "v1-normal",
                    "note": "", "settled": False, "outcome_yes": None,
                }
                with open(log_path, "a") as f:
                    f.write(json.dumps(entry) + "\n")
                if is_signal:
                    signals.append(entry)

    print(f"Evaluated {evaluated} markets, {len(signals)} signal(s) "
          f"at edge bar {edge_bar*100:.0f}c.")
    for s in sorted(signals, key=lambda x: -x["edge_c"]):
        print(f"SIGNAL {s['ticker']} {s['side']} ask={s['signal_price']:.2f} "
              f"x{s['contracts']} edge={s['edge_c']:.1f}c "
              f"min_left={s['min_left']:.0f} fair_yes={s['my_prob_yes']:.2f}")


if __name__ == "__main__":
    main()
