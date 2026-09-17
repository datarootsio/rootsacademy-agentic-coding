# Review feedback and final verification

This record covers the first visual refresh. The subsequent demo login/profile
extension is reviewed separately in [demo-login.md](demo-login.md); the original
backend comparison below describes the earlier checkpoint, not that extension.

Completed 17 September 2026. Three independent reviewers examined feature scope,
the UI, and tests. Their reports are [features.md](features.md), [ui.md](ui.md),
and [tests.md](tests.md).

## Feedback applied

| Finding | Resolution | Verification |
| --- | --- | --- |
| F1 / T2: old customer/date data remained visible during pending or failed reads | Invalidate the displayed snapshot, associate loaded data with customer and date, guard stale responses and errors, and expose loading/unavailable states with Retry. | Browser check reproduced the old failure before the fix. Final checks pass for delayed and failed customer/date reads, hidden old vouchers/history/deposits, retry, and superseded customer responses. Feature reviewer rechecked the fix. |
| T1: browser interactions lacked durable coverage | Added `app/frontend/tests/ui-smoke.js`, documented the Playwright CLI command, and included the script in ESLint. | Extended smoke suite passes; test reviewer confirmed coverage addresses T1/T2. |
| UI: Claim buttons clipped on mobile | Fit reward columns to the card width and allow reward names and prices to wrap. | UI reviewer rechecked 320px and 390px screenshots; automated checks confirm no reward-table horizontal scrolling at either width. |
| UI: duplicate Move money heading | Removed the redundant screen-reader heading. | Reviewer confirmed source change. |
| UI: favicon 404 | Added a local SS favicon and linked it in the HTML entry point. | Favicon served successfully; reviewer confirmed link. |

The dependency ignore rule also covers a local `node_modules` symlink, keeping
the dependencies reused for this development session out of version control.

## Final checks

- All 24 backend files remain byte-identical to accepted ticket 04 commit
  `a1f8c15c48f1e188530045b3c50aad5aa65ffb59`. No loyalty bonus or later domain
  behavior was introduced.
- Backend: **226 tests passed**, Ruff passed. Two dependency deprecation
  warnings remain; these are unrelated to the frontend changes.
- Frontend: ESLint, including the browser regression script, and Vite production
  build passed.
- Browser regression: navigation and form persistence; deposit and withdrawal;
  claim Cancel/Escape/focus/busy/confirmation/refusal; pending/failed date reads;
  pending/failed/superseded customer reads; retry; mobile layout and reward
  actions at 320px/390px; reduced motion; no uncaught browser exceptions.
- Expected HTTP errors were exercised deliberately for refused dates, an
  insufficient-points claim, and a simulated service outage.
- The completed project was not modified. The starter remains running at
  `http://127.0.0.1:5273` during this session.

No remaining blocking review findings. No commit or push was made.
