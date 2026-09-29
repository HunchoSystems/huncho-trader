# The Cycle

One cycle is: scan, paper-trade, settle, score, retro. Run it on whatever cadence fits (`./loop.sh --watch 60` for hourly). The cycle never places orders.

**What is and isn't automated:** `loop.sh` automates steps 1-2 only (screen + score). Steps 3-4 (retro write-up, playbook edits) are agent/operator steps: the operator's agent drafts them and the operator approves. The scripts never touch `journal/` or `strategy/`.

## 1. Screen (core/screen.py)

- Pull open events for each series in `config/settings.json` (default: KXETH15M, KXBTC15M).
- For each market: read the strike, minutes to close, and top of book.
- Fetch live spot (Coinbase) and estimate fair YES probability with the current model (v1: lognormal, no drift, vol from settings).
- Compute edge in cents vs the ask of the better side. Anything at or above `edge_bar_cents` is a signal, sized to `max_cost_per_trade`.
- **Log every evaluated market** to the paper log, signal or not, with the model's fair probability. The log is the training data. Log honestly: the number you write is the number you get scored on.

## 2. Settle + score (core/score.py)

- For each unsettled signaled market past its close, read Kalshi's official `result`.
- Score calibration: `brier_delta = Brier(market price) - Brier(my prob)`. Positive means the model beat the price.
- Simulate P&L as if every signal had been taken at the recorded ask (taker fills, fees included).
- Print the report: overall brier_delta, hit rate, simulated P&L, and per-category breakdown (asset x side x minutes-left).

## 3. Retro (journal/JOURNAL.md) - agent/operator step, not automated

After each scoring run, the operator's agent (or the operator by hand) writes a dated journal entry:

- What settled, and what the outcomes were.
- Where the model was right and where it was wrong (biggest estimation errors first).
- Whether any category is approaching the 10-signal evidence bar.
- **Playbook proposals**: numbered, each with the settled evidence behind it. Proposals the agent cannot enact itself (config changes, model changes, real-money changes) go in `journal/proposals.md` for the operator.

## 4. Self-edit (strategy/playbook.md) - agent/operator step, not automated

The agent may edit the playbook's strategy section (not the operator-owned guardrails at the top) when settled evidence supports it: keep, sharpen, or revert past edits. Every edit gets a dated note explaining what changed and why. The operator reviews every proposal before it lands. Commit it: the git log is the product.

## The daily deep retro (agent/operator step)

Once a day, the operator's agent does a slower pass: audit every playbook edit from the last 24h, re-grade the day's biggest errors, and adjudicate open proposals. This is where overfitting gets caught.
