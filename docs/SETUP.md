# Setup

Get from zero to a running paper loop in about 15 minutes. Paper trading costs
$0: Kalshi market data is free and no orders are placed.

## 1. Kalshi account

1. Create an account at [kalshi.com](https://kalshi.com) and complete identity verification.
2. Funding is **optional** for paper trading. Only fund if/when you enable real money (see REAL.md).

## 2. API key

1. Log in at kalshi.com, go to your profile/settings, and create an API key.
2. Give it **read** permission to start (trading permission only if you later enable real money).
3. Download the private key file. It is base64 text. **Never commit it to git.**

## 3. Machine setup

```bash
git clone https://github.com/<you>/huncho-trader.git
cd huncho-trader
pip install cryptography

# point the client at your key (pick ONE)
export KALSHI_KEY_ID="your-key-id-from-kalshi"
export KALSHI_KEY_PATH="$HOME/.kalshi/key.b64"   # put the downloaded key here, chmod 600
# ...or paste the base64 directly:
# export KALSHI_PRIVATE_KEY_B64="..."
```

Verify auth (read-only):

```bash
python3 core/kalshi_client.py "/trade-api/v2/portfolio/balance" --raw
```

You should see your balance JSON. If it errors, re-check the key id and key file.

## 4. First paper cycle

```bash
./loop.sh
```

This screens the open 15M windows, paper-logs every market it evaluates,
settles anything that closed, and prints the calibration report. With no
history yet, expect "No settled signals yet."

Run it on a loop:

```bash
./loop.sh --watch 15   # paper cycle every 15 minutes
```

Score any time:

```bash
python3 core/score.py
```

## 5. Tune (optional)

- `config/settings.json`: edge bar, per-trade cap, daily loss cap, series list, vol guesses.
- Copy it to `config/settings.local.json` for personal overrides (gitignored). If present, the scripts load it and merge it over `config/settings.json`, so your overrides apply without editing the committed file. Or just edit `settings.json` and commit the change so friends see it.

## 6. Real money (later, deliberately)

Read [REAL.md](../REAL.md) first. Short version: only after a category has 10+
settled paper signals with positive brier_delta, only with explicit human
enablement, only inside the hard caps. The loop can tighten the rules on its
own; it can never loosen them.

## Troubleshooting

- `Set KALSHI_KEY_ID`: the env var is missing in this shell. Export it (step 3).
- `Private key not found`: check `KALSHI_KEY_PATH` points at the downloaded key file.
- `ModuleNotFoundError: cryptography`: run `pip install cryptography`.
- Auth HTTP 401: the key id and private key must belong to the same API key; regenerate in Kalshi settings if unsure.
- No open windows found: the 15M series trades nearly 24/7, but listings can gap briefly. Wait a cycle.
