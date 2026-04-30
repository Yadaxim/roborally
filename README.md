# RoboRally

Web-based multiplayer replica of the RoboRally board game (original WotC rules).
Program your robot, race through a hazardous factory, touch the flags in order.

## Requirements

- Python 3.11+
- Node.js 20+

## Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run dev server
uvicorn server.main:app --reload

# Run tests
pytest

# Run a single test file
pytest tests/test_cards.py

# Run a single test
pytest tests/test_cards.py::TestDeck::test_deck_has_84_cards
```

## Frontend

```bash
cd frontend
npm install
npm run dev      # dev server at http://localhost:5173
npm test         # run tests (Vitest)
npm run build    # production build
```

## Project layout

```
backend/
  game/        # pure game logic (no I/O) — fully unit tested
  server/      # FastAPI app, WebSocket, room management
  tests/       # pytest test suite
  data/boards/ # board definitions (JSON)

frontend/
  src/
    components/game/   # react-three-fiber 3D scene
    components/ui/     # card hand, registers, lobby, player panels
    store/             # Zustand game state
    ws/                # WebSocket client
    __tests__/         # Vitest tests (store + WS logic)

plan/          # architecture doc and roadmap
research/      # game rules reference and implementation notes
```

## Development approach

TDD — tests are written before implementation.
See `plan/architecture_plan.md` for the full design and `plan/roadmap.md` for progress.
