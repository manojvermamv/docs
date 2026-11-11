# Options Basics — Buyer (2025 Edition)

A structured playbook for **retail options buyers** (NIFTY/BANKNIFTY intraday) to filter **TradingView signals (e.g., Supertrend)** with **1-min option chain OI + premium data**.

---

## 1. Core Signal Quadrants (Base View)

OI/Price quadrants originally made for futures — here reinterpreted for buyers:

* **Price ↑ & OI ↑** → Futures: long buildup. Buyer view: call buying okay **if premium ↑ + IV stable**.
* **Price ↓ & OI ↑** → Futures: shorts add. Buyer view: put buying okay **if premium ↑ + IV stable**.
* **Price ↑ & OI ↓** → Short covering. Buyer view: **avoid fresh OTM buying** (premium may not expand).
* **Price ↓ & OI ↓** → Long unwinding. Buyer view: weak trend → **avoid OTM**; ATM safer.

> ✅ For **options buyers**, never trust OI quadrant alone — confirm with **premium/IV move**.

---

## 2. Buyer-Specific Confirmations

### A. Premium vs Futures Move (Excess Check)

* Premium ↑ **faster** than futures → genuine buyer demand.
* Premium ↑ **slower** than futures → mostly sellers hedging → avoid.

### B. IV Direction

* IV ↑ + premium ↑ = strongest confirmation.
* IV ↓ while premium ↑ = **theta risk** → scalp only.

### C. Volume Delta

* Compare current 1-min volume vs rolling 20-bar avg.
* If ≥150% → fresh interest; else skip.

---

## 3. Put-Call Ratio (PCR)

Instead of static bands, use rolling percentiles (20-bar lookback):

* PCR < 25th percentile → call bias.
* PCR > 75th percentile → put bias.
* In-between → rely on price action + premium filter.

Fallback static: 0.7–1.3 = neutral, <0.7 = bullish, >1.3 = bearish.

---

## 4. Strike Selection (Buyer Bias)

* Default: **ATM or 1 ITM** strike (delta 0.45–0.55 for ATM, 0.55–0.65 for ITM).
* OTM buy only if: (1) volume surge, (2) IV ↑, (3) near breakout zone.
* Skip deep OTM — premium bleed risk.

---

## 5. Trade Filters (Pre-Trade Checklist)

1. TradingView signal (e.g., Supertrend flip).
2. Premium + OI alignment (excess check).
3. IV not collapsing.
4. Volume ≥150% of baseline.
5. PCR percentile agrees with bias.

Only if **≥4/5 checks true** → enter.

---

## 6. Risk & Execution Rules

* SL: **30–40% premium cut** or opposite OI build.
* Avoid last 30 min pre-expiry (IV crush).
* Avoid entries when PCR neutral + IV flat.
* Exit partial at 1R, trail balance.
* Don’t average losers (buyer rule #1).

---

## 7. India-Specific Notes

* Active session: **9:15 AM – 3:30 PM**.
* Avoid first 5 min (fake OI moves) + last 30 min (IV crush).
* Expiry Thursdays: OTM traps frequent → trade **ATM only**.
* Data vendors: smooth OI using 3-bar EMA to reduce ticks noise.

---

## 8. Practical Flow (Example)

1. Supertrend fires **Buy Call**.
2. Check CE ATM strike: premium ↑ 12, futures ↑ 8 (excess confirmed).
3. IV ↑, volume 170% baseline, PCR at 20th percentile.
4. Entry → SL 35% premium.
5. Exit half at 1R, rest trail until OI shift.

---

## 9. Quick Reference Table

| Condition      | Call Buy                     | Put Buy                      |
| -------------- | ---------------------------- | ---------------------------- |
| Price ↑ + OI ↑ | Yes if premium ↑ + IV stable | ✗                            |
| Price ↓ + OI ↑ | ✗                            | Yes if premium ↑ + IV stable |
| Price ↑ + OI ↓ | Avoid OTM                    | Avoid                        |
| Price ↓ + OI ↓ | ATM scalp only               | ATM scalp only               |

---

## 10. Final Rule of Thumb

**Options buyers survive only by filtering.**

* Signal + OI alone = trap.
* Signal + OI + premium + IV + volume = edge.

---
