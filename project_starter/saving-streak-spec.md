# Saving Streak — Feature Spec

> Domain spec for the running example used in the **AI Coding** module (`2026/curriculum/genai/18-9_AI Coding`).
> The exercises in `course.md` build the extensions defined here. Both documents must agree on these definitions.

## Problem Statement

Customers are rewarded for spending, not for saving. A customer who leaves money in a savings account gets an interest rate and nothing else — no visible, immediate acknowledgement that saving was the right call, and no reason to leave the money alone once it is in. The behaviour the bank wants to encourage (deposit, then don't touch it) is the behaviour that currently feels the least rewarding.

## Solution

**Saving Streak** rewards putting money into a savings account rather than spending it.

The base mechanic is deliberately minimal: a customer deposits money and earns points, full stop. **1 point per euro deposited, credited immediately, no conditions attached.** Points are redeemed against a small fixed-cost catalogue. Redemption is instant and final — once a reward is claimed the voucher or ticket is issued immediately and there is no reversal path.

Everything else in this spec — points expiry, the loyalty-rate bonus, peer-to-peer gifting, notifications — is an extension built on top of that base mechanic during the exercises. None of it exists on day one.

### Catalogue

| Reward | Cost |
|---|---|
| Cinema ticket (flagship item) | 100 points |
| Coffee or snack voucher | 40 points |
| Charity donation | 10 points |
| Family cinema pack (two tickets + a snack) | 180 points |

### Extensions

- **Points expiry.** Points expire after 12 months of inactivity, oldest first, via a scheduled batch job.
- **Loyalty-rate bonus.** A 10% bonus on a deposit's base points, paid once for every full 12 months that specific deposit stays untouched in the account. Each deposit runs its own recurring 12-month clock: on every anniversary it is still there, it earns another 10%. Withdrawing the deposit before an anniversary forfeits that year's bonus (bonuses already paid on earlier anniversaries stand), oldest deposit first when a withdrawal only partially covers what is outstanding.
- **Peer-to-peer gifting.** Customers can transfer points to each other, with no limit on frequency, amount per gift, or amount per day.
- **Notifications.** Balance thresholds, and a loyalty-rate bonus about to vest or about to be forfeited.

## Domain Vocabulary

Use these words consistently in code, tests, and tickets.

| Term | Meaning |
|---|---|
| **Points lot** | A quantity of points earned at one moment from one source (a deposit, a vested bonus, a received gift), carrying the earn date that drives its expiry. The unit of the points ledger. |
| **Deposit lot** | A quantity of money from one deposit, carrying its own recurring 12-month anniversary clock. The unit of the money-side ledger. Never leaves the customer it belongs to. |
| **Vest** | A deposit lot surviving an anniversary untouched, minting a bonus points lot. |
| **Forfeit** | A deposit lot (or part of one) being withdrawn before its next anniversary, giving up that year's bonus only. |
| **Sweep** | The scheduled batch pass that vests due bonuses and materialises expired points lots. |
| **Claim** | A redemption of points against a catalogue item. Instant, final, idempotency-keyed. |
| **Gift** | An irreversible transfer of points lots from one customer to another. |

## User Stories

1. As a savings customer, I want a point for every euro I deposit, so that saving feels rewarded and not just sensible.
2. As a savings customer, I want my points credited the instant the deposit lands, so that I do not have to wonder whether it worked.
3. As a savings customer, I want no conditions attached to earning, so that I do not have to read terms to understand the deal.
4. As a savings customer, I want to see my current points balance, so that I know where I stand against the catalogue.
5. As a savings customer, I want to see the history of how I earned and spent points, so that I can check the number is right.
6. As a savings customer, I want one points balance across all my savings accounts, so that I am not splitting my progress across products.
7. As a savings customer, I want to browse the reward catalogue with prices, so that I can pick something to save towards.
8. As a savings customer, I want to claim a cinema ticket for 100 points, so that I get the flagship reward.
9. As a savings customer, I want to claim a coffee or snack voucher for 40 points, so that a small balance is still worth something.
10. As a savings customer, I want to donate to charity for 10 points, so that I can do something other than consume with my balance.
11. As a savings customer, I want to claim a family cinema pack for 180 points, so that a long stretch of saving buys something worth sharing.
12. As a savings customer, I want my voucher issued immediately on claiming, so that I can use it now rather than wait for processing.
13. As a savings customer, I want to be told clearly before I claim that a claim cannot be undone, so that I am not surprised by finality.
14. As a savings customer, I want a claim I cannot afford to be refused cleanly, so that I never end up with a negative balance or a partial reward.
15. As a savings customer, I want a double-submitted claim to issue exactly one voucher, so that a flaky connection does not cost me 100 points.
16. As a bank operator, I want a reversed deposit to claw its points back, so that a bounced transfer does not mint points out of nothing.
17. As a savings customer, I want points I never touch to expire only after a full 12 months, so that the rule is generous enough to be fair.
18. As a savings customer, I want my oldest points spent first, so that expiry hits me as rarely as possible.
19. As a savings customer, I want expired points gone from my balance the moment they expire, so that I never see a number I cannot actually spend.
20. As a savings customer, I want a warning before points expire, so that I have time to spend them.
21. As a savings customer, I want a 10% bonus each year a deposit stays untouched, so that leaving money alone pays better than moving it.
22. As a savings customer, I want each deposit to run its own clock, so that a new deposit does not reset the progress of an older one.
23. As a savings customer, I want the bonus to keep paying every year the deposit survives, so that a long hold keeps earning.
24. As a savings customer, I want a partial withdrawal to cost me only the bonus on the part I withdrew, so that taking out 30 euros does not punish the 70 I left.
25. As a savings customer, I want bonuses already paid to stay mine, so that a withdrawal never claws back last year's reward.
26. As a savings customer, I want to know which deposits are closest to vesting, so that I can decide which money to take out.
27. As a savings customer, I want a warning before a withdrawal forfeits a bonus, so that I can wait a fortnight instead of losing it.
28. As a savings customer, I want to be told after the fact when a bonus was forfeited, so that I understand why my expected points did not appear.
29. As a savings customer, I want to gift points to another customer, so that I can pass a reward to someone who needs it more.
30. As a gifting customer, I want no limits on how often or how much I gift, so that the feature does not fight me.
31. As a receiving customer, I want gifted points to arrive immediately and spend like any other points, so that there is nothing special to learn.
32. As a bank operator, I want gifted points to keep their original expiry date, so that gifting cannot be used to reset expiry indefinitely.
33. As a gifting customer, I want a gift to a closed or unknown account refused before anything leaves my balance, so that points cannot vanish into nowhere.
34. As a savings customer, I want to be told when my balance crosses the price of something in the catalogue, so that I learn I can afford a reward.
35. As a savings customer, I want to turn off any category of notification, so that the feature does not become noise.
36. As a bank operator, I want every points movement recorded as an immutable ledger entry, so that any balance can be explained after the fact.
37. As a support agent, I want to see why a specific bonus did or did not vest, so that I can answer a customer's complaint with a fact.
38. As a bank operator, I want the nightly sweep to be safely re-runnable, so that a failed night can be replayed without double-crediting anyone.

## Implementation Decisions

### Boundaries and ownership

- **D1.** Saving Streak does not own the money. Core banking is the system of record and emits `MoneyDeposited`, `MoneyWithdrawn` and `DepositReversed`. Saving Streak consumes those and owns points.
- **D2.** Points balances are held **per customer**, not per account. One customer with three savings accounts has one balance.
- **D3.** Only external, customer-initiated credits earn points. Interest credits, internal transfers between the customer's own accounts, and refunds earn nothing — otherwise shuffling money between your own accounts prints points.
- **D4.** Deposits are floored to whole euros: €10.99 earns 10 points. Points are integers everywhere; there is no fractional point anywhere in the system.
- **D5.** All time arithmetic uses Europe/Brussels. The clock is injected, never read from a global, so tests can pin it.

### Two ledgers

- **D6.** There are **two** append-only ledgers, and they touch at exactly one point.
  - The **points ledger** holds points lots (earned) and consumption entries (claimed, gifted, expired, clawed back).
  - The **deposit-lot ledger** holds deposit lots on the money side and their consumption by withdrawals.
  - The only crossing: a vesting deposit lot mints a points lot.
- **D7.** No mutable balance field exists. Balance is derived from the points ledger, always excluding expired lots. This is what makes FIFO, expiry, and audit fall out of one structure instead of three.
- **D8.** Both ledgers consume **oldest first (FIFO)**. Spending points drains the oldest points lot; withdrawing money consumes the oldest deposit lot. One ordering rule, applied everywhere.

### Base mechanic

- **D9.** A deposit credits base points immediately and unconditionally. There is no hold period, no minimum, no cap.
- **D10.** Withdrawals never cost base points. "No conditions attached" means earning has no conditions; only the *bonus* is at risk from a withdrawal.
- **D11.** A reversed deposit claws back exactly the points it credited. The balance may go negative; claiming and gifting are blocked until it recovers. A deposit that never really happened must not leave points behind.

### Redemption

- **D12.** The catalogue is versioned data, not hardcoded config. A claim records the price it was claimed at, so a later price change never rewrites history.
- **D13.** Unlimited stock, no per-customer or per-period claim limits.
- **D14.** A claim the customer cannot afford is refused in full. No partial redemption, no negative balance, no paying the difference in cash.
- **D15.** Every claim carries a caller-supplied **idempotency key**. Replaying a key returns the original issued voucher rather than issuing a second one. This is non-negotiable given that issuance is irreversible.
- **D16.** Voucher issuance is delegated to an outbound port. If issuance fails, the points are not deducted; the claim fails as a unit.

### Expiry

- **D17.** **Expiry is per points lot, not per account.** Each lot expires 12 months after its earn date. Combined with FIFO consumption (D8), what expires is exactly what nobody touched for 12 months.
  - *This resolves a genuine ambiguity in the brief.* "12 months of inactivity" reads as an account-level clock, but "oldest first" is meaningless under an account-level clock — everything would expire at once. The per-lot reading is the only one where both phrases mean something, and it matches how loyalty schemes conventionally behave.
- **D18.** Expiry takes effect **the moment the clock passes**, not when the batch job runs. Reads exclude expired lots on the fly; the job only materialises the ledger entries. A late batch must never let someone spend dead points.
- **D19.** Vested bonus points are ordinary points lots earned on the vesting date, with their own fresh 12-month clock.
- **D20.** The sweep runs daily at 03:00 Europe/Brussels, is idempotent per business date, and catches up missed dates by running them in order.
- **D21.** Within one sweep, **vest before expire**, so a bonus vesting tonight is never swept the same night.

### Loyalty-rate bonus

- **D22.** Each deposit lot carries a recurring 12-month anniversary clock from its deposit date. On each anniversary it survives, it vests 10% of the base points of the **surviving portion**.
- **D23.** The bonus **never compounds**. It is always 10% of base, never 10% of base-plus-accrued. Year three on an untouched €100 pays 10 points, not 12.
- **D24.** Bonus points are floored to whole points. A €5 deposit lot vests 0 — correct and intentional.
- **D25.** A withdrawal consumes deposit lots oldest first and **splits** any lot it only partially covers. The withdrawn portion forfeits that year's bonus; the surviving portion **keeps the original anniversary date** and vests on schedule. Whole-lot forfeiture is rejected: it would punish a €1 withdrawal exactly as hard as a €100 one.
- **D26.** Bonuses already vested on earlier anniversaries are permanent. A withdrawal forfeits only the year in progress.
- **D27.** Anniversaries falling on a date that does not exist in the target month clamp to the last valid day: a 29 February deposit vests on 28 February in common years.
- **D28.** Forfeiture is recorded as an explicit ledger fact at withdrawal time, naming what was given up. Nothing is silently dropped.

### Gifting

- **D29.** A gift moves points lots from sender to recipient. It is irreversible and idempotency-keyed, exactly like a claim.
- **D30.** Gifted points **carry their original earn date**; the expiry clock does not reset. With unlimited frequency and amount, a fresh clock would let two accounts ping-pong points forever and never expire anything. One rule closes that loop without the rate limits the brief rules out.
- **D31.** Any unexpired points can be gifted — base or vested bonus alike — drained oldest first.
- **D32.** Deposit lots never move. Bonus entitlement is not transferable; the sender keeps their anniversary clocks intact.
- **D33.** Self-gifting is rejected. The recipient must be an enrolled, active customer; unknown or closed recipients are rejected before anything leaves the sender's balance.
- **D34.** A gift is atomic: both sides or neither.

### Notifications

- **D35.** Notifications leave through a single outbound port. Channel selection (push, email, in-app) belongs to whatever the bank already runs and is not Saving Streak's concern.
- **D36.** Delivery is at-least-once, deduplicated on (customer, notification type, trigger key).
- **D37.** **Balance thresholds are catalogue-anchored**, not arbitrary round numbers: 10, 40, 100 and 180. Each fires on upward crossing with a "you can now afford X" message, once per crossing, re-arming only after the balance falls back below it.
- **D38.** **Bonus about to vest**: 7 days before each deposit lot's anniversary, naming the amount.
- **D39.** **Bonus about to be forfeited** is two moments, because a withdrawal is instantaneous and cannot be pre-empted from nothing:
  - a **pre-confirmation** warning when core banking emits a `WithdrawalIntent` we can hook ("this forfeits 12 points vesting in 19 days"); and
  - an unconditional **post-hoc** notice when forfeiture actually happens.
  The intent hook degrades gracefully — no intent event, no warning, and the post-hoc notice still fires.
- **D40.** **Points about to expire**: 30 days ahead, aggregated per customer per day. Not in the original brief, added deliberately — points dying unannounced is the complaint that generates support tickets.
- **D41.** Per-category opt-out, default on. No quiet-hours logic; the sweep runs at 03:00 and the channel owns send timing.

### Seams

- **D42.** There is **one** seam: the application-service boundary that accepts domain events and commands (`deposit`, `withdraw`, `claim`, `gift`, `runDailySweep`) and returns results. Ledgers, the clock, the voucher issuer, and the notification port sit behind it as injected collaborators.
- **D43.** The daily sweep is invoked as a plain function at that same seam. Scheduling is infrastructure; the sweep itself must be callable directly from a test with a pinned date.
- **D44.** The stack is **Python** on the backend with a **local SQLite** database, and a **React + Vite** frontend. The domain logic stays framework-agnostic behind the D42 seam — the web framework, the SQLite persistence and the UI are all adapters around it, and the module is still about how the agent is directed, not about which framework wins.
- **D45.** A **thin demo UI** is part of the deliverable. It calls the D42 application-service seam over HTTP and holds no domain logic of its own: every rule lives behind the seam, and the UI is a window onto it. It exists so the feature is demoable in the session, not as a production interface.

## Testing Decisions

- **T1.** A good test here exercises **external behaviour at the single seam of D42**: send events and commands in, assert on balances, issued vouchers, ledger facts and emitted notifications. Never assert on ledger internals, lot identifiers, or the order of internal calls — those are exactly the details the exercises will refactor.
- **T2.** The clock is injected in every test. There is no `sleep`, no wall-clock dependency, and no test that behaves differently in January than in March.
- **T3.** Time-travel is expressed as advancing the injected clock and calling `runDailySweep` for each elapsed business date. This tests the real production path rather than a test-only shortcut.
- **T4.** The bonus and expiry rules get **table-driven** tests: deposit/withdrawal timelines in, expected vested and forfeited amounts out. These rules are where the edge cases live (partial withdrawal splits, 29 February, non-compounding, floor-to-zero) and prose alone will not pin them down.
- **T5.** Idempotency is tested by replaying the same key and asserting exactly one voucher, one gift, one balance change.
- **T6.** Every sweep test asserts re-runnability: running the same business date twice produces the same state.
- **T7.** Fakes, not mocks, for the voucher issuer and notification port — in-memory collaborators the test can inspect afterwards.
- **T8.** No prior art exists in this repo; these tests are the prior art for what follows.
- **T9.** The demo UI of D45 is **not** tested by asserting on components or internal UI state — that would contradict T1. It is verified by driving the running application end to end (browser or HTTP against the served frontend) and asserting on what the customer can see and do. The domain assertions stay at the D42 seam where T1 puts them; the UI check only confirms the seam is correctly surfaced.

## Out of Scope

- Movement of actual money. Opening accounts, executing deposits and withdrawals, interest calculation and payment.
- Authentication, authorisation, KYC and AML.
- The tax treatment of rewards, and any regulatory reporting on them.
- Multi-currency. Euros only; there is no FX anywhere in this spec.
- Voucher supplier integration beyond calling an issuance port, and anything about voucher redemption at the cinema or café.
- The charity side of a charity donation: selecting a charity, settling funds, issuing receipts.
- Anything beyond the thin demo UI of D45: production-grade UX, a design system, accessibility audits, responsive/mobile clients, and any UI state that is not read straight from the D42 seam.
- Rate limits, fraud detection and AML monitoring on gifting. Explicitly ruled out by the brief; D30 is what keeps expiry sound without them.
- Notification channels and their delivery infrastructure.
- Migration or backfill of points for existing customers.

## Further Notes

- **The base mechanic is a deliverable on its own.** Deposit, earn, claim — nothing else. It must be demoable before any extension is started, and the exercises depend on that being true.
- **Two ambiguities were resolved rather than guessed at**, and both are worth surfacing in the session because they are the module's actual lesson:
  - D17, where "12 months of inactivity" and "oldest first" contradict each other, and only one reading leaves both phrases meaning something.
  - D39, where "a bonus about to be forfeited" asks for a warning before an event nobody has announced yet.
- **D30 is the load-bearing decision on gifting.** The brief rules out limits on frequency and amount, which removes the usual defence against expiry-laundering. Carrying the original earn date across a transfer restores it with a single rule.
- **D25 is the load-bearing decision on the bonus.** Lot splitting on partial withdrawal is the difference between a rule customers experience as fair and one they experience as a trap.
