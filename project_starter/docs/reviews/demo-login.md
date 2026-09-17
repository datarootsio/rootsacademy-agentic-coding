# Demo accounts, login, and UI review

Reviewed on 2026-09-17 by an independent reviewer agent. Scope: the new demo
directory, one-time seeded histories, login/session selection, dashboard cleanup,
and regression coverage. Reward rules must remain limited to tickets 01–04.

## Findings

### P2 — Collapsed advanced references silently prevented submission (fixed)

Location: `app/frontend/src/App.jsx`, the deposit and withdrawal Advanced options
blocks (around lines 450 and 498).

Opening Advanced options, clearing the required reference, closing the section,
entering an amount, and submitting produced no visible validation or request.
Chrome logged an invalid form control that could not receive focus. This made the
form appear broken, despite a straightforward correction being possible.

The implementing agent added `onInvalidCapture` to open the section before native
validation focuses the invalid input, plus browser regression checks for both
forms. Independently retested both flows after the change: each section opens and
the reference field receives focus. No deposit or withdrawal was submitted.

### P3 — Mobile login headings join words across hidden line breaks (fixed)

Location: `app/frontend/src/Login.jsx:40` and `:53`, with mobile rules in
`app/frontend/src/index.css:778` and `:782`.

At widths of 760px and below the `<br>` elements become `display: none`, but the
adjacent text has no space. A 320px screenshot visibly reads “forgood things.” and
“thingstarts here.” Add explicit whitespace around those boundaries or use
responsive spans that retain word separation. A rendered-text assertion at the
mobile breakpoint would catch this; the existing overflow assertion does not.

Evidence before the fix: `output/playwright/starter-demo-review-login-mobile.png`
at repository root. The implementing agent added explicit JSX spaces and
rendered-text assertions. Independently checked after a fresh reload at 1280px,
390px, and 320px: both headings retain the required word separation.

## Verification and assessment

- Independently ran `uv run --extra dev pytest -q tests/test_demo.py`: **7 passed**.
  Tests cover three distinct profiles, seeded balances/history, repeated login,
  preservation of later activity, unknown emails, rollback/retry, and HTTP login.
- Independently ran `tests/login-smoke.js` against the running app in the isolated
  `starter-demo-review` browser session: **passed**, including real profiles,
  invalid email, normalized email, reload/session restore, sign-out, and widths
  1280px, 390px, and 320px. No demo balances were altered by the reviewer.
- Inspected the mobile login screenshot and reproduced/retested reference
  validation with real browser controls.
- Seeding uses the existing service inside an outer `BEGIN IMMEDIATE` transaction;
  the persisted seed marker is written only after successful history creation.
  Nested ledger operations join that transaction. No correctness or idempotence
  defect was found in this flow.
- Login selects explicitly documented shared demo identities. It does not claim
  to provide production authentication or access control. This matches the
  classroom application's scope.
- No loyalty-bonus vesting, gifting, streak multiplier, or notification behavior
  was added. Sample history exercises deposits, FIFO withdrawals, points expiry,
  and catalogue claims already present in the starter.
- The full backend suite, lint/build, and broader interaction smoke results were
  reported by the implementing agent; this review independently reran the focused
  checks above rather than claiming a duplicate full run.

No blocking backend or reward-scope issue was found. Both actionable UI findings
were fixed by the implementing agent and independently verified. No unresolved
review findings remain.
