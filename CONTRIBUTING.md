# Contributing

1. Create a focused branch from `main`.
2. Install backend development dependencies with `pip install -r backend/requirements-dev.txt`.
3. Install frontend dependencies with `npm ci` in `frontend/`.
4. Run `cd backend && python -m pytest` and `cd frontend && npm test && npm run build`.
5. Do not commit `.env` files, API keys, SQLite databases, or private recruiter data.

Keep changes small, preserve demo mode without provider keys, and add regression
tests for behavior changes.
