# Binding Product-Scope Decision

The project currently supports and develops only two strategy families:

1. **Options Buyer**
2. **Options Seller**

Do not expand the project into additional trading markets or standalone instrument strategies without a new explicit owner decision.

## Priority 1 — Preserve complete market evidence

Continuously capture and verify all market evidence required to reproduce, evaluate and audit options-buyer and options-seller decisions:

* Spot and option-chain snapshots.
* One-minute OHLCV.
* Ticks where required.
* Bid, ask and spread where upstream provides them.
* Volume and open interest.
* Greeks, including their source and validity indicators.
* Instrument, strike, expiry and DTE.
* Market-data source.
* Observation timestamp and monotonic sequence.
* Missing, stale, zero-filled or upstream-failed fields.
* Exchange-rule and contract-regime boundaries.

Quality flags must distinguish:

* Genuine zero.
* Missing value.
* Unsupported upstream field.
* Stale value.
* Failed request.
* No process running.
* No subscription.
* Reconstructed historical value.

Never silently substitute zero for missing market evidence.

Expired contracts must remain reproducible before their upstream history disappears. Historical sessions lacking full chains, spreads or fills must be labelled according to their actual evidence quality and must not be presented as complete evidence.

## Included

### Options Buyer

* Buying call options.
* Buying put options.
* BuyerEdge and future options-buying strategies.
* Long-premium entries and exits.
* Premium-based stops and trailing protection.
* Theta-decay, IV, liquidity and spread analysis.
* Strike, expiry and DTE selection.
* Buyer-specific costs, slippage and risk limits.

### Options Seller

* Selling call options.
* Selling put options.
* Hedged or multi-leg option-selling structures when explicitly declared by the strategy.
* Short-premium entries, adjustments and exits.
* Margin and available-funds checks.
* Defined-risk and undefined-risk classification.
* Seller-specific stop, hedge and square-off behaviour.
* Gamma, vega, theta and expiry risk.
* Multi-leg partial-fill and orphan-leg protection.
* Seller-specific charges, slippage and capital limits.

Options selling must not silently reuse options-buyer assumptions. It requires its own:

* Strategy manifest and configuration profile.
* Position lifecycle.
* Risk limits.
* Margin checks.
* Cost model.
* Fill and slippage model.
* Protection policy.
* Replay validation.
* Research evidence.
* Capital allocation.
* Promotion evidence.

## Supporting data allowed

The project may capture and use the following when they support options buying or options selling:

* Underlying index spot price.
* Futures reference price or synthetic-futures value.
* Option chains.
* Bid, ask and spread.
* Volume and open interest.
* IV and Greeks.
* Expiry calendar and DTE.
* Market regime and liquidity measurements.
* Broker positions, orders, trades, funds and margin.

Spot or futures data may be used as an input, reference, hedge measurement or pricing signal. This does **not** authorize standalone equity or futures trading.

All supporting data must retain its source, timestamp, sequence, validity and quality status. Reconstructed or derived values must be explicitly identified as such and must not be represented as direct upstream observations.

## Explicitly outside current scope

Do not build, optimize or activate:

* Cash-equity trading strategies.
* Standalone futures strategies or futures orders.
* Commodity trading.
* Currency or forex trading.
* Cryptocurrency trading.
* Bonds or fixed-income trading.
* International market expansion.
* Additional asset classes.
* Generic multi-asset portfolio optimization.
* Market-coverage expansion performed merely to collect more data.

Do not interpret “collect diverse evidence” as “add more markets.”

Evidence diversity must currently come from within options buying and selling:

* Different expiries.
* Different DTE bands.
* Different strikes and moneyness.
* Different IV conditions.
* Trending and ranging sessions.
* Event and non-event sessions.
* Different liquidity and spread conditions.
* Buyer versus seller behaviour.
* Different option structures where explicitly supported.

## Separate buyer and seller authority

Options Buyer and Options Seller must be treated as separate strategy and risk families.

Each must have independently declared:

* Strategy identity.
* Enabled status.
* `none`, `plan` or `trade` authority.
* Capital allocation.
* Maximum loss.
* Maximum exposure.
* Maximum open positions.
* Allowed structures.
* Allowed expiries and strikes.
* Required market inputs.
* Execution policy.
* Protection policy.
* Research lineage.
* Performance attribution.

The AI must not dynamically switch a strategy from buyer to seller, or seller to buyer, unless that behaviour is explicitly declared, bounded and approved as part of the strategy contract.

An advisor response must not gain seller authority merely because it returns `SELL`. Order side and strategy family are different concepts:

* An options buyer uses `BUY` to enter and `SELL` to exit.
* An options seller uses `SELL` to enter and `BUY` to exit.

The strategy manifest and position lifecycle—not the model’s text—must determine which meaning applies.

## Options-seller safety requirements

Before an options-selling strategy receives live authority, verify:

1. Broker margin and available funds are fresh.
2. Worst-case exposure is computable or the order is refused.
3. Required hedge legs are identified.
4. Multi-leg order sequencing is deterministic.
5. Partial fills cannot leave an unmanaged naked position.
6. Orphan-leg detection and recovery exist.
7. Position limits cover every leg and the combined structure.
8. Gap and expiry risk are represented.
9. Stop and emergency-exit behaviour are replayed and sandbox-tested.
10. Broker square-off and expiry handling are attributable.
11. Costs are seller-side aware.
12. Account-level portfolio limits include buyer and seller positions together.
13. Required market evidence is complete and sufficiently fresh for the proposed structure.
14. Missing, stale, reconstructed or upstream-failed fields cannot be mistaken for valid observations.

If the system cannot safely evaluate margin, exposure, hedge state, remaining risk or required market evidence, it must refuse the seller entry.

## Updated project direction

Continue improving the shared deterministic framework, but validate every change against both supported families:

```text
Options Buyer Intent ─┐
                      ├─→ Shared deterministic planning and risk
Options Seller Intent ┘        ↓
                       Execution Gateway
                              ↓
                       OpenAlgo and Broker
                              ↓
                  Reconciliation and attribution
```

Shared infrastructure may include:

* Market capture.
* Complete evidence preservation.
* `MarketView`.
* Strategy runtime.
* Intent contracts.
* Planning gates.
* Execution gateway.
* Order FSM.
* Reconciliation.
* Replay.
* AI lineage.
* Research lifecycle.
* Monitoring and operations.

Buyer and seller policies must remain separate where their economics or risks differ.

Market capture and replay must preserve enough evidence to determine:

* What was observed.
* When it was observed.
* Which source supplied it.
* Whether it was direct, reconstructed, stale, missing or failed.
* Which contract and exchange rules applied.
* Whether the evidence was sufficient for the resulting decision.
* Whether expired instruments remain reproducible.

## Maintainer decision rule

For every proposed feature, ask:

> Does this directly improve the safety, evidence, research, execution or operation of an options-buyer or options-seller strategy?

* If **yes**, continue through the normal evidence and verification process.
* If **no**, classify it as outside the current scope.
* If uncertain, stop and request an owner decision.
* Never expand market coverage by assumption.
* Never weaken evidence quality by silently filling, substituting or relabelling missing data.
* Never treat incomplete historical sessions as complete evidence.

The immediate objective is therefore:

> Prove and improve genuine net edge across options buying and options selling, using complete and accurately labelled market evidence and the existing deterministic execution foundation, without expanding into additional markets or standalone asset classes.
