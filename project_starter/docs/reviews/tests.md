# Test review — starter visual refresh

Reviewed 2026-09-17, before review feedback implementation. Scope: the redesigned starter frontend, retaining the ticket 01–04 backend. This report records the initial findings; subsequent fixes should record their verification separately.

## Evidence

- Independently ran the starter backend suite using the completed project's installed Python dependencies, explicitly setting `PYTHONPATH` to `project_starter/app/backend/src`: **226 passed**, 2 dependency deprecation warnings, 1.73 seconds. No completed-project source was used for the tested application.
- The backend tests exercise earning, claims and idempotency, refusal, expiry/as-of reads, daily sweeps, FIFO deposit lots, persistence and reversals. No backend rule changes are needed for this visual refresh.
- Inspected `app/frontend/package.json`: only dev, build, preview and lint scripts exist; there is no durable frontend interaction regression suite at review time. Build/lint therefore cannot validate the new conditional navigation or native dialog lifecycle.
- Executed browser checks against `http://127.0.0.1:5273` in isolated Playwright session `starter-tests-review` with customer `tests-review-20260917`. All five navigation destinations rendered. The reward dialog opened, initially focused Cancel, closed with Escape, restored focus to the initiating Claim button, and closed after an insufficient-points refusal while exposing the refusal as an alert. All assertions passed.
- The browser's only incidental resource failure was a missing favicon; the claim refusal produces an expected failed HTTP response. Neither prevented the checked flows.

## Findings and targeted recommendations

### T1 — Medium: preserve browser-level coverage of the changed interactions

`app/frontend/src/App.jsx` introduces conditionally mounted pages and `ClaimConfirmation`, neither covered by the 226 Python tests. Add a small durable browser smoke check, with a documented execution command, that verifies actual user behavior rather than component structure:

1. Visit Overview, Move money, Rewards, History and Demo tools, and confirm the intended page is visible.
2. Enter a deposit, navigate away/back, and verify form state persists; post a deposit and confirm the refreshed balance/deposit appears.
3. Open a reward claim, cancel with both Cancel and Escape, verify no points were spent, and verify focus returns to Claim. Confirm an affordable claim and verify one voucher and the expected points change; exercise a refusal and the busy state.
4. Check as-of context remains visible after changing pages and returning to today refreshes all customer data.

These checks are justified by the interaction changes; avoid introducing redundant Python tests for unchanged domain behavior.

### T2 — Medium: regression-test customer/date isolation during asynchronous reads

The initial `refresh` implementation retains the previous `balance`, `movements`, `claims` and `depositLots` until all new requests resolve. A different customer/date can therefore be displayed with the preceding snapshot while loading, or indefinitely after a failed read. The feature review independently reported the same issue.

After fixing the snapshot lifecycle, add a deterministic browser check with delayed/failed responses: show customer A data, switch to B and verify A's balances/vouchers/lots/history are immediately absent; fail B's read and verify explicit error/retry with no A data; allow a newer request to finish before an older request and verify the older result cannot repaint the screen. Repeat the loading/failure check when changing the viewing date. This is a meaningful isolation assertion, not an implementation-mirroring test.

## Conclusion

Backend regression coverage passes. The checked dialog and navigation behavior passes in a real browser. Address T1/T2 with a focused frontend smoke check and the customer/date snapshot fix, then run the check against the final frontend. No additional domain test expansion is requested.

## Feedback verification

Reviewed the added `app/frontend/tests/ui-smoke.js`, its README execution command, the ESLint inclusion of browser checks, and the revised snapshot lifecycle in `App.jsx`.

- **T1 addressed:** a durable browser check now covers the five navigation destinations, form persistence, deposits/withdrawals and refreshed balances, both claim cancellation paths, initial/restored focus, confirmation busy state, voucher issuance and refusal. It additionally checks narrow viewport clipping and reduced motion.
- **T2 addressed:** deterministic delayed/failed requests assert that previous customer balances, vouchers, history and deposit lots are absent during loading; failed reads keep old figures hidden; Retry loads the intended customer; a superseded response cannot repaint it. A separate delayed/refused viewing-date scenario verifies hidden previous figures and return-to-today recovery. The implementation clears snapshots, binds successful data to the customer/date, and guards completion/error publication against superseded reads.
- No further significant test-coverage issue found within this refresh's scope. This follow-up verifies the test code and fix by inspection; the parent agent is executing the final extended browser suite and should record its execution outcome in the feedback resolution report.
