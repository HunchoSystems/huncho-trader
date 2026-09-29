# Huncho Trader

**A self-improving paper-trading loop for Kalshi prediction markets.** When the operator runs or schedules the cycle, it scans short-term markets, scores its own calibration after every settled market, and proposes playbook updates from the results. Real money only follows settled evidence, and stays small and capped.

Inspired by [bennyjo/phil](https://github.com/bennyjo/phil), rebuilt native for [Kalshi](https://kalshi.com): US-regulated, with an official trading API.

## The experiment

An agent gets a simulated bankroll and Kalshi's short-term crypto windows (ETH and BTC 15-minute up/down markets). Every cycle it scans the open windows, estimates fair value with its current model, and paper-logs every market it evaluates. When windows settle, it scores its own calibration against the price it would have paid, using Brier score. The agent then writes a retrospective and proposes playbook edits, which the human operator reviews and applies. Nothing here runs on its own: the operator starts the loop (`./loop.sh --watch`) or schedules it, and the retro and playbook-edit steps are agent-assisted, never performed by the scripts themselves.

Three layers keep it honest:

- a **screen-score cycle** (`loop.sh`, `core/`) that the operator runs on a schedule: it screens, paper-trades, settles, and scores;
- a **retro pass** that audits every playbook edit (keep, sharpen, or revert) and grades the biggest estimation errors (`journal/`);
- the **human operator**, who owns the protected config (`config/settings.json`, the caps, the real-money switch). Evidence flows in through `journal/JOURNAL.md`. Change proposals the agent cannot make itself go in `journal/proposals.md`.

The playbook's git log is the product: every commit is a lesson the agent paid for (in paper). The honest metric is `brier_delta`, not P&L: is the agent's probability a better forecast than the market's own price?

## Two loops: paper learns on schedule, real money follows the evidence

The learning engine is paper. A repeatable loop cycles across the short-term market universe when the operator runs it, because simulated feedback loops cost nothing and answer the question that matters: *in which market categories does fast estimation actually beat the price?*

Real execution rides on top, deliberately small and **off by default**. See [REAL.md](REAL.md). When the operator enables it, only edge classes with positive settled evidence get real stakes, sized inside hard caps in `config/settings.json`. Paper fills are honest: recorded at the live ask, settled at Kalshi's official resolution.

## Honest-simulation rules

- Paper entries are recorded at the live ask (like a real taker), never the mid.
- Entry prices are recorded at scan time; resolutions are Kalshi's own.
- The agent cannot loosen `config/settings.json` caps or flip the real-money switch. Those are operator-owned.
- Caps: $2 max per trade, $5 daily loss cap, one open position, no entries under 3 minutes to close.
- The private key is never in this repo. It lives in an env var or a local file (see [docs/SETUP.md](docs/SETUP.md)).

## Run

```bash
# one-time setup
cp config/settings.json config/settings.local.json   # optional overrides (gitignored)
export KALSHI_KEY_ID="your-key-id"
export KALSHI_KEY_PATH="$HOME/.kalshi/key.b64"       # or KALSHI_PRIVATE_KEY_B64
pip install cryptography

# paper loop (costs $0: no orders, free market data)
./loop.sh                 # one paper cycle: screen, log, settle, score
./loop.sh --watch 15      # paper cycle every 15 minutes
python3 core/score.py     # calibration report any time
```

## Repo map

- `core/kalshi_client.py` - signed Kalshi API client (env-based key, no secrets)
- `core/screen.py` - scans 15M windows, v1 vol model, paper-logs every market
- `core/score.py` - settles paper trades, Brier scoring, calibration report
- `config/settings.json` - edge bar, caps, sizing, model params (operator-owned)
- `strategy/playbook.md` - the current strategy, rewritten from settled evidence
- `journal/` - dated retros and playbook proposals
- `CYCLE.md` - the hourly procedure. `REAL.md` - the real-money policy.
- `docs/SETUP.md` - full setup: Kalshi account, API key, funding, first run

## Disclaimer

Research experiment in agent self-improvement. Paper trading only by default. Real-money trading on Kalshi involves risk of loss; nothing here is financial, investment, or betting advice. Past paper performance predicts nothing. Know your own rules before running anything with real funds.

## License

[Apache-2.0](LICENSE). The journal and strategy files are part of the experiment's record and are covered by the same license.
