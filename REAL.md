# Real Money Policy

Paper is the learning engine. Real money follows the evidence, deliberately small, and is **off by default** (`config/settings.json`: `real.enabled: false`).

## When real money is allowed at all

1. The operator (a human) explicitly enables it. The agent cannot flip the switch.
2. Only edge classes (asset x side x minutes-left) with **10+ settled paper signals AND positive average brier_delta** qualify. Everything else stays paper.
3. A category with negative brier_delta over 10+ settled signals is cut, even if it once qualified.

## Hard caps (operator-owned; the agent cannot loosen these)

- `per_bet_cap`: max total cost per trade including fees (default $1).
- `per_day_cap`: max total risked per day (default $5).
- `max_open_positions`: 1. One position at a time.
- Limit orders only, at the signal price or better. Never market orders.
- No entries under 3 minutes to close.

## Fill accounting

Real fills feed back into the journal: compare actual fill quality against the simulated taker-fill model. If real fills are systematically worse than paper assumed, the model or the edge bar must change.

## The operator's checklist before enabling

- [ ] Kalshi account funded with money you can afford to lose.
- [ ] API key created with trading permission; key id + private key in env (never in the repo).
- [ ] At least one category has 10+ settled paper signals with positive brier_delta.
- [ ] Caps reviewed and set in `config/settings.json`.
- [ ] You understand every trade can lose the full stake.

Nothing here is financial advice. Prediction-market trading can lose money. Size accordingly.
