# Institutional Trading Phenomena 🏛️

A structured, institutional-grade taxonomy of **trading phenomena** used by buy-side firms, prop desks, execution teams, and quantitative funds.

> This repository focuses on **how markets actually work**, not retail indicators or signal-based strategies.

---

## Core Philosophy

Retail traders ask:
> *“Which indicator gives buy/sell signals?”*

Institutions ask:
> **“Where is liquidity, who is trapped, and how can size be executed with minimal impact?”**

Indicators are **measurement tools**, not decision-makers.

---

## 1. Price Action & Candle Geometry Phenomena

### Candle Geometry
- **Body–Wick Imbalance**  
  Measures aggression vs rejection  
  *Indicator:* Wick-to-body ratio, volatility-normalized

- **Displacement Candles**  
  Sudden repricing driven by institutional intent  
  *Indicator:* Candle size > X × ATR with low overlap

- **Compression (Volatility Squeeze)**  
  Pre-expansion positioning  
  *Indicator:* ATR contraction, Bollinger Band squeeze

---

## 2. Market Structure Phenomena

### Structural Mechanics
- **Break of Structure (BOS)**  
  Trend continuation confirmation  
  *Indicator:* Swing high/low violation with displacement

- **Market Structure Shift (MSS / CHoCH)**  
  Regime change detection  
  *Indicator:* First counter-trend BOS after accumulation

- **Internal vs External Structure**  
  Entry vs directional bias  
  *Indicator:* Multi-timeframe swing logic

---

## 3. Liquidity & Stop Mechanics 💧

Institutions trade **liquidity**, not price.

### Liquidity Phenomena
- **Equal Highs / Equal Lows**  
  Stop-loss clustering zones  
  *Indicator:* Swing clustering within tick tolerance

- **Liquidity Sweep / Stop Hunt**  
  Engineered move before reversal  
  *Indicator:* Sweep + immediate displacement

- **Buy-Side vs Sell-Side Liquidity**  
  Directional targeting framework  
  *Indicator:* Resting highs/lows above or below range

---

## 4. Order-Flow & Execution Phenomena

### Order Behavior
- **Order Blocks (OBs)**  
  Institutional inventory zones  
  *Indicator:* Last opposing candle before displacement

- **Mitigation Blocks**  
  Rebalancing institutional exposure  
  *Indicator:* Return to OB with declining volume

- **Iceberg Orders**  
  Hidden execution of large size  
  *Indicator:* Repeated absorption at same price (DOM / footprint)

- **Absorption vs Aggression**  
  Determines control of auction  
  *Indicator:* High volume with minimal price movement

---

## 5. Price Inefficiency Phenomena

Markets are structurally inefficient.

### Inefficiencies
- **Fair Value Gaps (FVG / Imbalance)**  
  Return to institutional fair pricing  
  *Indicator:* Three-candle imbalance (no overlap)

- **Volume Gaps / Thin Liquidity Zones**  
  Rapid price traversal zones  
  *Indicator:* Volume Profile voids

- **Single Prints (Auction Theory)**  
  Rejected price levels  
  *Indicator:* Market Profile single TPOs

---

## 6. Volume & Auction Theory Phenomena

### Auction Dynamics
- **Volume Climax**  
  End of auction phase  
  *Indicator:* Volume spike + failed continuation

- **Value Area Shift**  
  Institutional repricing  
  *Indicator:* Session VWAP and Value Area migration

- **High Volume Nodes (HVN)**  
  Balance and acceptance zones  
  *Indicator:* Volume Profile peaks

---

## 7. Statistical & Quantitative Phenomena 📊

### Statistical Effects
- **Mean Reversion**  
  Return to statistical equilibrium  
  *Indicator:* Z-score, VWAP deviation

- **Momentum Persistence**  
  Trend continuation tendency  
  *Indicator:* Rolling returns, autocorrelation

- **Volatility Clustering**  
  Volatility regimes persist  
  *Indicator:* Rolling standard deviation, GARCH

- **Statistical Arbitrage**  
  Relative mispricing exploitation  
  *Indicator:* Spread Z-score (pairs / baskets)

- **Regime Change Detection**  
  Structural market shifts  
  *Indicator:* Variance breaks, HMMs

---

## 8. Time-Based Phenomena ⏱️

Institutions trade **time** as much as price.

### Temporal Effects
- **Kill Zones / Session Opens**  
  Liquidity injection windows  
  *Indicator:* Session-based volatility expansion

- **Time-Based Mean Reversion**  
  Intraday equilibrium behavior  
  *Indicator:* Session VWAP bands

- **End-of-Day Rebalancing**  
  Portfolio and benchmark flows  
  *Indicator:* Volume surge near close

---

## 9. Cross-Market & Correlation Phenomena

No asset trades in isolation.

### Intermarket Effects
- **SMT Divergence (Smart Money Technique)**  
  Hidden accumulation or distribution  
  *Indicator:* Correlated asset divergence

- **Lead–Lag Relationships**  
  Predictive asset sequencing  
  *Indicator:* Cross-correlation analysis

- **Risk-On / Risk-Off Flows**  
  Capital rotation behavior  
  *Indicator:* Bonds vs equities vs USD

---

## 10. Macro & Fundamental Flow Phenomena 🌍

### Capital Flow Effects
- **Index Rebalancing Flows**  
  Forced institutional transactions  
  *Indicator:* Weight-change projections

- **Earnings & Event Drift**  
  Post-event inefficiencies  
  *Indicator:* Volatility skew analysis

- **Rate Expectations & Yield Curves**  
  Macro directional bias  
  *Indicator:* Futures-implied rates

---

## 11. Execution & Microstructure Phenomena

### Execution Mechanics
- **VWAP / TWAP Execution**  
  Benchmark-neutral execution  
  *Indicator:* VWAP deviation bands

- **Dark Pool Prints**  
  Hidden institutional activity  
  *Indicator:* Off-exchange volume spikes

- **Market Impact Decay**  
  Post-execution normalization  
  *Indicator:* Mean reversion after large trades

---

## Final Notes

- Institutions combine **3–5 phenomena**, not dozens.
- Most indicators are **derivatives of price, volume, and time**.
- Edge comes from **context, confluence, and execution discipline**.

---

### Suggested Next Extensions
- Phenomena → strategy mapping
- Institutional myths vs reality
- Indicator design for measurement (not signals)
- Multi-timeframe institutional models

---

**Disclaimer:**  
This repository is for **educational and research purposes only**. Nothing here constitutes financial advice.
