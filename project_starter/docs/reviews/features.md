# Feature review

Reviewed 2026-09-17 against accepted ticket 04 checkpoint
`a1f8c15c48f1e188530045b3c50aad5aa65ffb59`.

## Result

The feature boundary is correct. No loyalty bonus or later functionality was
introduced. The initial review found one medium-priority frontend state issue,
inherited from the checkpoint. It has been resolved; see feedback verification
below.

## Finding F1 — P2: stale data is relabelled as another customer or date

**Evidence:** `app/frontend/src/App.jsx:140–166` clears displayed data only when
the customer ID is empty. A nonempty customer change or viewing-date change
starts asynchronous reads but keeps the old balance, deposit lots, history, and
vouchers on screen. The new customer field and date banner already identify the
new query. The catch handler at lines 201–204 adds an error without invalidating
the old snapshot. Request numbering correctly rejects late responses but does
not prevent already-rendered data from appearing under another customer/date.

**Reproduction:** Load a customer with deposits, then change to another nonempty
customer while the network is slow. The previous customer's money and points
remain visible while loading. If a read fails, those figures remain indefinitely.
Likewise, select an unsupported far-future viewing date (for example 9999-12-31):
the request is refused but the overview still presents the earlier figures under
the new date banner.

**Recommendation:** Track snapshot identity and request loading/error state.
Clear or hide values whenever the displayed customer/date no longer matches the
loaded snapshot; show a loading/unavailable state instead of interpreting empty
arrays as genuine zero holdings. Preserve existing abort and latest-read guards.
Guard error publication against superseded reads as well. Add a regression check
with a delayed customer read and a rejected date read.

## Verified scope and preserved behavior

- Compared all 24 tracked backend files, including tests and configuration,
  byte-for-byte against the checkpoint: no differences.
- Frontend still sends the same money-deposited, money-withdrawn,
  deposit-reversed, claim, and daily-expiry requests to the existing API.
- Deposit source selection, event references, and claim idempotency keys remain
  supported. The claim confirmation retains the finality warning and duplicate
  submission guard, with a modal dialog added for presentation.
- Customer selection, point balance/history, deposit lots, reward catalogue,
  issued vouchers, reading as of a date, and today's expiry sweep remain
  reachable through the new navigation.
- Deposit anniversary dates were already part of ticket 04. Displaying them does
  not implement bonus vesting. There are no later-feature API calls for bonus
  payouts, early-withdrawal bonus forfeiture, gifting, notifications, weekly
  streaks, savings-high calculations, authentication, or new account management.
- The updated README explicitly distinguishes implemented ticket 01–04 behavior
  from the complete target specification.

## Validation limits

This review used source inspection and a Git-content comparison. The stale-state
finding follows directly from the state update paths; this reviewer did not run
a browser reproduction or rerun tests. Runtime/UI and test execution are covered
by the separate reviews and implementation verification.

## Feedback verification

F1 is resolved in the revised frontend. Source review confirms that `refresh`
invalidates the previous snapshot, clears its values, and scopes both success and
failure publication to the current request/customer/date. The `loadedFor`
identity gate prevents an old snapshot from rendering even before the new
customer/date effect runs. Balances, deposit lots, vouchers, and history all use
that gate and distinguish loading/unavailable data from real empty holdings.
Failed reads now provide a Retry action. A read failure following a successful
write also no longer removes the successful transaction or voucher banner.

The implementation agent reports reproducing F1 before the fix and passing
browser regressions afterward for pending/failed customer reads and a failed date
read. This follow-up independently checked the source fix; it did not rerun
those browser scenarios. No further feature findings were identified in this
fix, and no backend changes were requested.
