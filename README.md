# RoboRally

Web-based multiplayer replica of the RoboRally board game (original WotC rules).
Program your robot, race through a hazardous factory, touch the flags in order.

## Status

**Backend complete** — all game logic, WebSocket server, Dizzy Highway board, 234 passing tests.  
**Frontend skeleton** — Vite + React + TypeScript, Zustand store, WS client wired up. 3D rendering next.

## Requirements

- Python 3.11+
- Node.js 20+

## Running the game

```bash
# 1. Start the backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn server.main:app --reload
# → API at http://localhost:8000

# 2. Start the frontend
cd frontend
npm install
npm run dev
# → App at http://localhost:5173
```

Open two browser tabs, enter the same room ID with different player names, click **Join**, then **Start Game** in either tab.

## Tests

```bash
# Backend (pytest)
cd backend
pytest                             # all 234 tests
pytest tests/test_activation.py   # single file

# Frontend (Vitest)
cd frontend
npm test                           # all 9 store tests
npm run test:watch                 # watch mode
```

## Project layout

```
backend/
  game/        # pure game logic (no I/O) — fully unit tested
  server/      # FastAPI app, WebSocket, room management
  tests/       # pytest test suite
  data/boards/ # Dizzy Highway board JSON

frontend/
  src/
    components/game/   # react-three-fiber 3D scene (in progress)
    components/ui/     # card hand, registers, lobby, player panels
    store/             # Zustand game state
    ws/                # WebSocket client + message dispatch
    types/             # TypeScript types mirroring backend schemas

plan/          # architecture doc and roadmap
research/      # game rules reference and implementation notes
```

## WebSocket protocol

All messages are JSON `{ type, ...payload }`.

| Direction | type | When |
|---|---|---|
| C→S | `join` | First message, creates/joins room |
| C→S | `start` | Start the game |
| C→S | `submit_registers` | Submit 5 cards |
| S→C | `joined` | Confirm join |
| S→C | `game_started` | Game begins, sends robot list |
| S→C | `deal_hand` | New hand of cards |
| S→C | `phase_change` | Phase transition |
| S→C | `state_sync` | Reconnect: full state snapshot |
| S→C | `register_events` | One register's animation events |
| S→C | `game_over` | Winner announced |

## Development approach

TDD — tests written before implementation.  
See `plan/architecture_plan.md` for design and `plan/roadmap.md` for progress.
