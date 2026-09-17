# Saving Streak — starter

This starter was imported from `rootsacademy-prep`. Its original domain checkpoint is commit
`a1f8c15c48f1e188530045b3c50aad5aa65ffb59`, the accepted ticket 04 checkpoint.
The reward and deposit rules come from that commit. A demo profile directory,
one-time sample history, and passwordless demo login have been added for classroom
use. The frontend offers Overview, Move money, Rewards, and History.

Implemented:

- Earn points on deposits, with duplicate-event handling and deposit reversals.
- Redeem rewards from the catalogue.
- Spend the oldest points first and expire points after twelve calendar months.
- Track deposit lots and consume the oldest deposits first on withdrawal.

Loyalty bonus vesting (ticket 05), gifting, streak multipliers, and notifications
are not implemented.
Deposit anniversary dates are already available as groundwork for that exercise.
`saving-streak-spec.md` contains the full target specification, including features
still to be built; it is not a list of completed starter features.

## Demo login

Choose a profile on the login screen or enter its email. No password is needed.

| Profile | Email | Starting scenario |
| --- | --- | --- |
| Anke Peeters | `anke@example.com` | Savings history, expired points, and a cinema voucher |
| Bram De Vos | `bram@example.com` | Points nearing expiry and a coffee voucher |
| Lina Janssens | `lina@example.com` | A fresh savings account |

Each profile has its own Everyday savings account. History is generated through
the existing application service on first login. Later logins and server restarts
preserve balances, purchases, and original dates. The selected email is remembered
in the current browser tab; Sign out clears it.

This is demo identity selection, not production authentication: the classroom
event API remains accessible and the demo profiles are shared. No real money moves.
Each profile receives €2,500 in a spending account once, alongside its existing
savings. Overview shows total money, the active savings account, spending funds,
and points separately. Deposits move spending funds into savings; withdrawals
move savings back into spending. Both preserve total money. The server checks
account ownership, available funds, and whole cents, with atomic, idempotent
transfers. Relogin and restart never refill spending funds.

The UI uses `/api/demo/transfers` and `/api/demo/customers/{id}/accounts`.
The original `/api/events/*` endpoints still represent events already accepted by
core banking, for curriculum exercises; they are not customer transfer commands.
Deposit and withdrawal references are generated automatically for retries.
Reversals, historical reads, and expiry sweeps are available through the backend event API.

## Run locally

From this folder, start the backend in one terminal:

```sh
cd app/backend
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m uvicorn saving_streak.api:app --host 127.0.0.1 --port 8787
```

Start the frontend in another terminal:

```sh
cd app/frontend
npm ci
npm run dev
```

Open http://127.0.0.1:5273. The starter creates its own
SQLite database at `app/backend/saving-streak.db`.

## Checks

```sh
# From app/backend
.venv/bin/python -m pytest
.venv/bin/ruff check .

# From app/frontend
npm run lint
npm run build
```

With both servers running, run the browser regression check from `app/frontend`:

```sh
npx --yes --package @playwright/cli playwright-cli --session starter-smoke open http://127.0.0.1:5273
npx --yes --package @playwright/cli playwright-cli --session starter-smoke run-code --filename tests/login-smoke.js
```

The login check uses the real demo profiles without spending their points.
For the interaction check, start an isolated API and frontend in two terminals:

```sh
# From app/backend; restart before each smoke run for fresh balances
PYTHONPATH=src .venv/bin/python tests/serve_ui_fixture.py

# From app/frontend
SAVING_STREAK_API=http://127.0.0.1:8788 npm run dev -- --port 5274
```

Then, from `app/frontend`:

```sh
npx --yes --package @playwright/cli playwright-cli --session starter-smoke run-code --filename tests/ui-smoke.js
```

The interaction check selects isolated fixture identities at login and exercises
real transfer and reward endpoints against a temporary database. It covers
balances, transfer limits and persistence, navigation, reward confirmation and
refusal, keyboard focus, customer read failures, delayed responses, mobile
layouts, and reduced motion. The API tests also cover overdrafts, concurrent
transfers, retries, account ownership, precision, and rollback.

The independent feature, UI, and test review reports and the feedback resolution
record are in `docs/reviews/`.

The demo login extension has its own [implementation review](docs/reviews/demo-login.md).
Both reported UI findings were fixed and independently rechecked. Final validation:
248 backend tests, Ruff, frontend ESLint/build, real-login smoke, and the extended
interaction smoke all pass.
