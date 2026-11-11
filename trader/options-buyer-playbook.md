# 📈 Options Buyer Playbook (Price–OI–Greeks, Edition · 2025)

> Built for **retail options buyers** in Indian indices (NIFTY/BANKNIFTY). Assumes regular session **09:15–15:30 IST**. Use responsibly with position sizing and hard exits.

---

## 📘 Overview

As an **options buyer**, you only profit when **direction + timing + volatility** work together. Traditional “Price–Volume–Open Interest” (P–V–OI) quadrants were designed for **futures**; for **options**, add two more lenses:

1. **Premium behaviour vs Delta** (is the option moving more than the underlying would imply?)
2. **Implied Volatility (IV)** direction (is volatility being bought or sold?)

This guide converts classic OI logic into a buyer-centric checklist, clarifies **when to buy CE/PE**, and highlights **when to skip**.

---

## 🔎 Price–OI Core Map (Futures View → Buyer Context)

> Treat **volume** as *confirmation*, not the main quadrant label. Compare volume to a **rolling average** (e.g., 20 bars) on your working timeframe.

| Underlying Price | OI | Futures Read   | Buyer Context (CE/PE)                                                                           |
| ---------------- | -- | -------------- | ----------------------------------------------------------------------------------------------- |
| ↑                | ↑  | Long build-up  | Bullish continuation **possible** → Look for CE **only if** options confirm (see next section). |
| ↑                | ↓  | Short covering | Rally **fragile** → Usually **avoid** fresh CE buys unless options show real demand.            |
| ↓                | ↑  | Short build-up | Bearish continuation **possible** → Consider PE **only if** options confirm.                    |
| ↓                | ↓  | Long unwinding | Selling pressure **easing** → **Wait** for a base/turn; avoid chasing PE.                       |

> **Why this matters:** OI counts *positions*, not *direction*. You infer side from **price**, **premium move**, and **IV**.

---

## 🎯 Options-Buyer Overlay (Premium & IV)

Use this to confirm whether the options market is **buying risk** (good for buyers) or **supplying/writing** (bad for buyers).

| Underlying | Option Leg | ΔOI | Premium (LTP) vs Delta | IV  | Likely Flow                           | Buyer Friendly?                           |
| ---------- | ---------- | --- | ---------------------- | --- | ------------------------------------- | ----------------------------------------- |
| ↑          | Calls      | ↑   | **↑ beyond delta**     | ↑/≈ | **Call long build-up** (demand)       | ✅ CE                                      |
| ↑          | Calls      | ↑   | ↑ ≈ *delta-only*       | ↓   | **Call writing/supply**               | ❌ Avoid CE                                |
| ↓          | Puts       | ↑   | **↑ beyond delta**     | ↑   | **Put long build-up** (demand)        | ✅ PE                                      |
| ↑          | Puts       | ↓   | ↓                      | ↓   | **Put longs unwinding / short cover** | ✅ Bullish for underlying (but not for PE) |

**How to compute “beyond delta” (quick heuristic):**
`excess_move = % option_return − (delta × % underlying_return)`
Excess > 0 with IV ↑ ⇒ buyers likely lifting offers. Excess ≤ 0 with IV ↓ ⇒ writers supplying.

> **Volume use:** Prefer CE/PE strikes with **above-avg volume**, **tight spreads**, and **stable top-of-book depth**. Illiquid OTM strikes distort signals.

---

## ✅ When to Buy (CE/PE)

### ✔️ Buy **CALL (CE)** when **all** apply

* Underlying **rising** with structure (breakout or trend resumption)
* **Call OI ↑**, **Call premium ↑ beyond delta**, **IV ↑ or stable**
* Volume **above** rolling average (on both underlying and chosen strike)
* Market not entering a known **IV-crush window** (post-event/late expiry day)

**Strike bias:** **ATM or 1-step ITM** for better delta, faster capture; avoid thin OTM unless momentum is strong.

---

### ✔️ Buy **PUT (PE)** when **all** apply

* Underlying **falling** with breakdown/clean lower-highs
* **Put OI ↑**, **Put premium ↑ beyond delta**, **IV ↑**
* Volume **above** rolling average; no nearby major support

**Strike bias:** **ATM or 1-step ITM**; avoid thin OTM puts unless volatility expansion + momentum align.

---

### ❌ Don’t Buy (common traps)

* Price ↑ but OI ↓ and options show **IV ↓ / excess ≤ 0** → **short covering / writing**
* OI **dropping** on both CE & PE → trend **exhaustion/no conviction**
* **High IV** before entry (paying up) unless expecting **big** move **soon**
* **Rangebound** market (theta burn) or **expiry-day pin** near your strike
* **Far OTM** with low volume / wide spreads / jumpy marks

---

## 📌 ATM Strike Selection — Quick Map

| Regime      | Action     | CE/PE OI Signal | Volume vs Avg | Options Read (IV/Excess)        | Buyer? |
| ----------- | ---------- | --------------- | ------------- | ------------------------------- | ------ |
| Strong Up   | Buy CE     | CE OI ↑         | ↑             | Premium ↑ beyond delta & IV ↑/≈ | ✅      |
| Weak Up     | Avoid      | Mixed/↓         | ↓/≈           | IV ↓, premium ≈ delta → writing | ❌      |
| Strong Down | Buy PE     | PE OI ↑         | ↑             | Premium ↑ beyond delta & IV ↑   | ✅      |
| Weak Down   | Avoid/Wait | Mixed/↓         | ↓/≈           | Put premium softens             | ❌      |
| Sideways    | Avoid      | Mixed/flat      | ≈             | Choppy, time decay              | ❌      |

---

## 🧭 PCR (Put/Call Ratio) — Use as a **Context Filter**, not a trigger

* Prefer **rolling percentiles** over fixed levels.

  * Bullish bias: **PCR below \~30th percentile** of recent history
  * Bearish bias: **PCR above \~70th percentile**
* If you want fixed guides: **< 0.9** (bullish tilt), **> 1.3** (bearish tilt). Always confirm with **options overlay** above.
* Use **equity options PCR** when possible to reduce index-hedging noise.

**Fast table**

| PCR State           | Read         | Typical Use                      |
| ------------------- | ------------ | -------------------------------- |
| Low (<30p or <0.9)  | Bullish tilt | Prefer CE **if** options confirm |
| Neutral (\~1.0)     | Mixed        | Skip until clarity               |
| High (>70p or >1.3) | Bearish tilt | Prefer PE **if** options confirm |

---

## 🧮 Strike Selection Heuristics

**Delta-based (recommended):**

* **ATM (Δ≈0.5)** for fast directional moves.
* **1-step ITM (Δ≈0.6–0.7)** for higher win-rate, less theta shock.

**Premium-proxy (quick & dirty):**

```
Select Strike ≈ Spot ± (1 × ATM Premium)
```

Use with caution; confirm **liquidity**, **IV**, and **excess\_move**.

**Choose ITM when:** trend is confirmed, IV is not collapsing, premium affordable.
**Choose ATM when:** move has started, confirmation strong, you want speed without big outlay.
**Avoid OTM when:** near expiry, weak momentum, or spreads are wide.

---

## 📅 India-Specific Execution Notes (NSE)

* **Session**: 09:15–15:30 IST. Signals near close may be distorted by **expiry pinning** & **MM hedging**.
* **Weekly expiry churn**: Expect noisy OI changes; de-weight last **30–45 min** on expiry days.
* **Rollover/Calendar effects**: OI can rise without clean directional intent — don’t over-read raw OI.
* **Data cadence**: Vendor updates may batch at 1–3 minutes. Smooth with a **3–5 bar median/z-score** for ΔOI and Δpremium.
* **Theta edge**: For buyers, **Mon/Tue** entries generally beat late-week entries (all else equal).

---

## ✅ Visual Checklist (Pre-Trade)

```
TREND
[ ] Structure break (BO/BD) or trend resumption
[ ] Underlying volume > rolling avg

OPTIONS CONFIRMATION
[ ] Target strike liquid (tight spread, steady depth)
[ ] ΔOI up on my side (CE for up, PE for down)
[ ] Premium ↑ beyond delta (excess_move > 0)
[ ] IV ↑ or stable (no imminent IV-crush window)

SENTIMENT CONTEXT
[ ] PCR supportive (low for CE, high for PE) — or percentile-based

RISK
[ ] Fixed SL in premium (e.g., 25–35%) or structure-based
[ ] Time stop (e.g., exit if thesis fails in N bars)
[ ] Size small; no averaging losers
```

---

## 🧾 Ideal Strike in a Slow Positive Market

| Criterion          | Preference                 | Rationale                                   |
| ------------------ | -------------------------- | ------------------------------------------- |
| Most Traded        | ✅ Yes                      | Liquidity → tighter spreads/easier exits    |
| Highest OI         | ⚠️ With IV/premium confirm | High OI alone can be **writers**            |
| Strike Type        | ✅ ATM or 1-step ITM        | Better delta, survivability vs theta        |
| Time to Expiry     | ✅ **≥ 5 days**             | Reduces theta drag                          |
| Implied Volatility | ❌ Avoid very high IV       | Overpaying → poor RR unless expecting surge |

---

## 🧠 Option Greeks (Buyer View)

| Greek | Meaning                         | Buyer Use                                                       |
| ----- | ------------------------------- | --------------------------------------------------------------- |
| Delta | Price sensitivity to underlying | Aim **0.5–0.7** for CE/PE (ATM→ITM) for a balance of speed/odds |
| Theta | Time decay                      | Avoid late-week entries; use **time stops**                     |
| Vega  | Sensitivity to IV               | Prefer **low-to-moderate IV** entries; benefit if IV expands    |
| Gamma | Rate of delta change            | High early-week → faster payoffs when trend persists            |

**Quick tips**: High delta = more responsive; high theta = bleed; low-IV entry + expected expansion = tailwind; high gamma + clean momentum early in week = sweet spot.

---

## 🌀 Implied Volatility (IV) — Practical View

| IV State | Premium      | Buyer Stance                          |
| -------- | ------------ | ------------------------------------- |
| High     | Expensive 🔺 | Avoid unless **imminent** large move  |
| Low      | Cheaper 🔻   | Favour entries pre-breakout/news      |
| Rising   | Premium ↑    | Tailwind **if already long**          |
| Falling  | Premium ↓    | Headwind — avoid buying into IV crush |

**IV Tips**

* Buy when IV is **low** but a **catalyst/technical trigger** is near.
* Avoid when IV is **elevated** without a strong timing edge.
* Use **Vega** to gauge sensitivity; know your **IV-crush windows** (post-event, expiry-day late session).

---

## 🧠 Bonus: Quick Action Reference

| Market Signal                               | Action | Reason                                     |
| ------------------------------------------- | ------ | ------------------------------------------ |
| Price ↑ + Vol ↑ + OI ↑ + CE overlay bullish | Buy CE | Strong bullish momentum, risk being bought |
| Price ↓ + Vol ↑ + OI ↑ + PE overlay bullish | Buy PE | Strong bearish momentum, risk being bought |
| Price ↑ + OI ↓ + IV ↓ / excess ≤ 0          | Avoid  | Short covering / call writing              |
| Price ↓ + OI ↓                              | Avoid  | Long unwinding; wait for setup             |

---

## 🧰 Risk & Process (Non‑Negotiables)

* Fixed **premium SL** (e.g., 25–35%) **or** structure-based invalidation — *choose one before entry*.
* **No averaging down**; scale **out** into strength.
* **Journal**: capture entry context (trend, ΔOI, IV, excess\_move, PCR percentile).
* **Post-trade review** weekly to refine thresholds (PCR bands, volume lookback, IV bands).

---

## 🧾 Bottom Line (2025)

> **“Buy only when price, options flow (ΔOI + excess premium), and IV align — or don’t buy at all.”**

Stay patient. Let the market **show demand for options** (not just underlying) before you pay premium.


---

## 📊 PCR Live Dashboard Reference

| Source         | Link                                                                 | Notes                        |
|----------------|----------------------------------------------------------------------|------------------------------|
| NSE            | [NSE Option Chain](https://www.nseindia.com/option-chain)            | Official OI & PCR data       |
| Sensibull      | [Sensibull Option Chain](https://web.sensibull.com/optionchain)      | PCR + strategy               |
| NiftyTrader    | [NiftyTrader](https://www.niftytrader.in/nifty-put-call-ratio)                               | Clean UI for data            |
| TradingView    | Custom OI/PCR indicators                                              | Needs setup                  |
