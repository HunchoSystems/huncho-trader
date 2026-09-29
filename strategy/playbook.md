# Playbook (v1)

## Operator-owned guardrails (the agent does not change these)

- Edge bar: 8c per contract minimum, defensible.
- Limit orders only, at the agreed price or better. Never market orders.
- $2 max total cost per paper trade incl. fees. $5 daily loss cap.
- One open position at a time. Never force a trade.
- Fresh re-verification of the quote immediately before any real order.
- Pause after 2 executed real trades for a performance review.

## Strategy (rewritten from settled evidence; latest first)

### v1 - 15M crypto windows, lognormal v1 model (genesis)

- Universe: KXETH15M and KXBTC15M (ETH/BTC 15-minute up/down).
- Model: P(expiry spot >= strike) from a lognormal with no drift; vol from
  `config/settings.json` (ETH 0.60, BTC 0.55 annualized). These vols are
  starting guesses, not estimates. The journal tracks whether they calibrate.
- Signal: model edge vs the ask of the better side >= 8c, 3+ minutes to close.
- Sizing: floor(max_cost / ask) contracts, reduced until cost + fees <= $2.
- Working hypothesis: books reprice fast; signals older than a few minutes are
  usually stale. Re-verify every quote before acting.
- Open question: is the v1 vol too hot or too cold? The settled brier_delta
  by minutes-left bucket will tell.

## Change log

- 2026-09-26: v1 written at genesis. No settled evidence yet.
