# Roots Academy — Agentic Coding

Build the Saving Streak loyalty bonus using an agent-assisted delivery loop.

- [Exercises](exercises.md)
- [Starter setup and demo accounts](project_starter/readme.md)
- [Business specification](project_starter/saving-streak-spec.md)
- [UML comparison](docs/uml/README.md)

## Start the project

Requires Python 3.10+ and Node.js 20+ with npm.

Backend, from the repository root:

```sh
cd project_starter/app/backend
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m uvicorn saving_streak.api:app --host 127.0.0.1 --port 8787
```

Frontend, in another terminal from the repository root:

```sh
cd project_starter/app/frontend
npm ci
npm run dev
```

Open http://127.0.0.1:5273 and choose a demo profile. Each profile starts with
€2,500 in spending funds alongside its sample savings history.

The starter includes earning and redeeming points, points expiry, deposit tracking,
and funded deposits and withdrawals. The loyalty bonus and later features remain
exercises. See the starter README for test commands and the exact feature scope.

The UML diagrams compare two completed implementations. They are reference material
for the architecture exercise, not diagrams of the starter.
