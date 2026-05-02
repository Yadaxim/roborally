# RoboRally – Roadmap

Status legend: ⬜ not started · 🔄 in progress · ✅ done

---

## Phase 1 — MVP (playable game)

### Backend scaffolding
- ✅ Project skeleton (`pyproject.toml`, `requirements.txt`, folder structure)
- ✅ pytest configured and running

### Game engine (TDD — in order)
- ✅ Cards & deck — all 7 types, 84-card counts, priority numbers, dealing, hand size
- ✅ Board model — tile types, wall representation, coordinate helpers
- ✅ Robot model — position, facing, damage counter, archive marker
- ✅ Push chains — single push, chain push, blocked by wall
- ✅ Laser tracing — ray cast, wall blocking, robot blocking (closer absorbs)
- ✅ Conveyor logic — single step, express (2 steps), turning conveyors rotate robot
- ✅ Full register activation — all 8 sub-steps in correct order
- ✅ Game state machine — lobby → programming → activation → game_over
- ✅ Win condition — checkpoint sequencing, victory detection

### Server
- ✅ FastAPI app + WebSocket endpoint
- ✅ Room creation and joining (2–4 players)
- ✅ Deal cards, accept register submissions, broadcast activation events
- ✅ 30s programming timer with auto-submit
- ✅ Reconnection handling — state_sync on rejoin

### Board data
- ✅ Board JSON format finalised
- ✅ Dizzy Highway board (12×12, 3 checkpoints, conveyors, gears, pits, laser)

### Frontend scaffolding
- ✅ Vite + React + TypeScript project skeleton
- ✅ Vitest configured and running (9 store tests)
- ✅ Tailwind CSS wired up
- ✅ WebSocket client + Zustand store skeleton

### 3D rendering (react-three-fiber)
- ✅ Canvas, lighting, OrthographicCamera
- ✅ Isometric ↔ top-down camera toggle (lerp animation)
- ✅ Floor tile geometry and basic materials
- ✅ Wall segments on tile edges
- ✅ Pit tiles (missing floor, dark hole)
- ✅ Checkpoint tiles (flag pole)
- ✅ Conveyor tiles (arrow indicator)
- ✅ Gear tiles (disc on surface)
- ✅ Robot meshes (cylinder + box, one colour per player)
- ✅ Robot movement animation (@react-spring/three)
- ✅ Robot rotation animation

### Card UI
- ✅ Card component (type icon, priority number)
- ✅ Hand display (dealt cards, used cards dimmed)
- ✅ Register slots (drag-and-drop via dnd-kit, click to remove)
- ✅ Locked register display
- ✅ Confirm button + programming timer countdown

### Game UI
- ✅ Lobby — join/create room, Enter key, disabled button until inputs filled, room/name shown after join
- ✅ Player panel — health bar (9 segments), lives (hearts), checkpoint dots, recent event log
- ✅ Round result overlay (damage taken, checkpoints reached)
- ✅ Game over screen — standings sorted by flags/damage, Play Again button
- ✅ "Waiting for others…" shown after submitting registers (replaces Confirm button)

### Animation
- ✅ Stepped register playback — register_events queued and played back move-by-move before snapping to authoritative state; smooth spring-physics robot movement

---

## Phase 2 — Polish

### Lobby overhaul

- ✅ **Room list on entry screen** — server sends `room_list` to every new connection; player sees joinable rooms with a Join button; `GET /rooms` HTTP endpoint also available
- ✅ **Create room flow** — host picks a room name and required player count (2/3/4); room gets an auto-generated 4-letter ID
- ✅ **Roster panel** — waiting room shows all players with host badge and ready status; `roster_update` broadcast on every join/leave
- ✅ **Ready system** — per-player Ready toggle; game starts automatically when all players are ready; host has a Force Start button
- ✅ **Minimum player enforcement** — `can_force_start` requires ≥ 2 players; `all_ready` requires the room's `required_players` count

- ⬜ Pause button — host can pause/unpause the game; freezes the programming timer and delays activation until resumed

- ⬜ Live camera angle slider (elevation + rotation) for isometric view tuning

- ⬜ Laser beam visual (red line flash + fade)
- ⬜ Damage animation (robot flashes red)
- ⬜ Destroy / reboot animation (robot sinks, reappears at archive)
- ⬜ Conveyor belt scroll animation
- ⬜ Gear rotation animation
- ⬜ 2–3 additional boards
- ⬜ Option cards (draw at double-wrench repair sites)
- ⬜ Power-down mechanic
- ⬜ Mobile-friendly layout

---

## Phase 3 — Extensions

- ⬜ In-browser board editor
- ⬜ Sound effects
- ⬜ Spectator mode
- ⬜ Expansion tile types (oil slicks, portals)
- ⬜ Persistent room codes (share link to invite friends)

---

## Completed
- ✅ Backend scaffolding (pyproject.toml, requirements, folder structure, pytest)
- ✅ Cards & deck (14 tests: card types, counts, priorities, dealing, hand size)
- ✅ Board model (46 tests: tile types, walls, bounds, movement, direction utils, JSON loading)
- ✅ Robot model (35 tests: position, facing, rotation, movement, damage, locked registers, archive, respawn)
- ✅ Push chains (16 tests: single push, chain push, wall blocking, board edge destruction, pit destruction)
- ✅ Laser tracing (19 tests: ray cast, wall blocking, multi-beam damage, robot blocking, robot lasers)
- ✅ Conveyor logic (17 tests: green/express movement, chaining, turning rotation, blocking)
- ✅ Game state machine (21 tests: phases, hand dealing, register submission, win condition)
- ✅ Lobby overhaul — room browser, create-room flow, roster panel, ready system, force start (24 new server tests)
