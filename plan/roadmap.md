# RoboRally – Roadmap

Status legend: ⬜ not started · 🔄 in progress · ✅ done

**Related docs:** `plan/architecture_plan.md` (stack and structure), `plan/plan.md` (upgrades, alternate modes, UI protocols). **Rules:** `research/game_rules.md` (consolidated across editions).

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
- ✅ Full register activation — all 8 sub-steps in correct order; checkpoint/repair tiles heal damage when resolving flags / wrench sites (rules-aligned hand size)
- ✅ Game state machine — lobby → programming → activation → game_over
- ✅ Win condition — checkpoint sequencing, victory detection

### Server
- ✅ FastAPI app + WebSocket endpoint
- ✅ Room creation and joining (currently 1–4 players; extend to 8 for WotC 1994 parity — see Phase 2 checklist)
- ✅ Deal cards, accept register submissions, broadcast activation events
- ✅ Programming phase — 30s countdown **starts when the first player submits** (multiplayer rules); incomplete registers at timeout filled with **random** cards from remaining hand; `your_program` message syncs authoritative cards before activation
- ✅ Reconnection handling — state_sync on rejoin

### Board data
- ✅ Board JSON format finalised
- ✅ Dizzy Highway board (12×12, 3 checkpoints, conveyors, gears, pits, laser)

### Frontend scaffolding
- ✅ Vite + React + TypeScript project skeleton
- ✅ Vitest configured and running (store tests in `gameStore.test.ts`)
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
- ✅ Register slots (drag-and-drop via dnd-kit; click or drag back to hand to clear slot)
- ✅ Locked register display
- ✅ Confirm button + programming timer (shows “—” until first lock-in, then countdown)

### Game UI
- ✅ Lobby — join/create room, Enter key, disabled button until inputs filled, room/name shown after join
- ✅ Player panel — health bar (9 segments), lives (hearts), checkpoint dots, recent event log
- ✅ Round result overlay (damage taken, checkpoints reached)
- ✅ Game over screen — standings sorted by flags/damage, Play Again button
- ✅ "Waiting for others…" shown after submitting registers (replaces Confirm button)

### Animation
- ✅ **Eight sub-step batches per register** — each rules phase (program cards, conveyors express/normal, pushers, gears, crushers, lasers, checkpoints) is a separate `register_events` message with `substep_id` / index; sequencer plays each batch before advancing
- ✅ Smooth stepped playback — snap to authoritative `robots` state after every batch; spring-physics robot movement between moves

---

## Phase 2 — Polish

### Lobby overhaul

- ✅ **Room list on entry screen** — server sends `room_list` to every new connection; player sees joinable rooms with a Join button; `GET /rooms` HTTP endpoint also available
- ✅ **Create room flow** — host picks a room name and required player count (2/3/4 for now); room gets an auto-generated 4-letter ID
- ✅ **Roster panel** — waiting room shows all players with host badge and ready status; `roster_update` broadcast on every join/leave
- ✅ **Ready system** — per-player Ready toggle; game starts automatically when all players are ready; host has a Force Start button
- ✅ **Minimum player enforcement** — `can_force_start` allows solo (≥ 1 player); `all_ready` requires the room's `required_players` count (currently 1–4; align with 8 when lobby supports it)
- ✅ **Live room list for browsers** — connections still picking a room receive pushed `room_list` when any lobby room is created, joined, starts a match, or a player leaves (no reload)

## GAMEPLAY

- ✅ Pause button — host can pause/unpause the game; freezes the programming timer and delays activation until resumed
- ✅ **Activation HUD beside board** — during playback, shows current register (1–5), the local player’s programmed card for that register, and the **active rules sub-step** name + progress (e.g. Express conveyors 2/8)

- ✅ Live camera angle slider (elevation + rotation) for isometric view tuning — panel bottom-left in isometric mode; orbit 0–360°, elevation 15–75°; smooth lerp to target

- ✅ Laser beam visual (red line flash + fade during lasers sub-step)

- ⬜ Damage animation (robot flashes red)
- ⬜ Destroy / reboot animation (robot sinks, reappears at archive)
- ⬜ Conveyor belt scroll animation
- ⬜ Gear rotation animation
- ✅ Additional boards — Cannery Row, Exchange, Pit Maze, Maelstrom (`backend/data/boards/*.json`)
- ✅ Map selection in lobby — host chooses board; `GET /boards` manifest; `set_board` WebSocket; create-room `board_id`; room list shows map name
- ⬜ Game mode selection in lobby — host selects Standard / King of the Hill / Capture the Flag / Demolition Derby / Free for All; `ModeSelector` UI; `set_mode` WebSocket message
- ⬜ Option cards (draw at double-wrench repair sites) — original WotC edition; 26 base cards + Armed & Dangerous expansion
- ⬜ Upgrade cards (2016/Renegade edition) — energy system, upgrade shop phase, 25 permanent + 17 temporary cards; full passive effects in engine (see `research/game_rules.md` — Renegade / 2016 sections)
- ⬜ Power-down mechanic
- ⬜ Mobile-friendly layout

### Original WotC (1994) edition — rules completeness

Cross-check with `research/game_rules.md` for wording. The MVP engine already covers shared 84-card deck, 9 minus damage hands, register locks, eight activation sub-steps, push chains, conveyors, lasers, checkpoints, crushers, lives/respawn at archive with 2 damage. Remaining or partially aligned items:

- ⬜ **Virtual robots** — two robots on one square: one is “virtual” (board elements affect it; it cannot push or be hit by *robot-mounted* lasers); at end of each register, if alone on the square it becomes real again
- ⬜ **End-of-round repair** — after all five registers, robots still on any wrench or checkpoint tile heal **one additional** damage (separate from checkpoint/repair resolution in the checkpoints sub-step of each register)
- ⬜ **Double-wrench site (full choice)** — heal 1 **or** 2 damage (player choice), **or** draw one option card once the option deck exists (current behaviour always heals 2)
- ⬜ **Locked registers visible to opponents** — locked slots and their program cards are public information during programming and activation
- ⬜ **Power down (full rule)** — player announces before the relevant point in the turn sequence; robot skips movement and robot laser for that activation; at **end** of that turn all damage cleared and locks freed; clarify same rule vs “announce before programming” variant in `research/game_rules.md`
- ⬜ **Powered-down robot vs factory** — resolve precisely with the rulebook: whether conveyors, pushers, and gears still affect the robot; whether board lasers and crushers can still damage or destroy it during that turn
- ⬜ **Sacrifice option to cancel a hit** — discard an option card to absorb one damage when the option system exists
- ⬜ **Destruction strips options** — on respawn, lose held option cards (per original edition)
- ⬜ **Up to 8 players / robots** — original supports 2–8; raise server and lobby caps above 4; eight start positions and colours/UI
- ⬜ **Docking Bay** — optional first board or annex with eight docking squares feeding the factory course (component-accurate setup vs start positions embedded in one board JSON)
- ⬜ **Win by elimination** — if all opponents are eliminated (0 lives), last surviving robot wins the standard race (even if it has not finished the flag sequence)
- ⬜ **Duplicate register program when 9 damage** — robot repeats previous round’s five cards automatically; verify edge cases (new game, first round) and sync to clients

---

## Phase 3 — Extensions

- ⬜ In-browser board editor
- ⬜ Sound effects
- ⬜ Spectator mode
- ⬜ Expansion tile types (oil slicks, portals, energy spaces)
- ⬜ Persistent room codes (share link to invite friends)
- ⬜ King of the Hill game mode — scoring per-register, hill tile type, score target config
- ⬜ Capture the Flag game mode — flag objects, teams, carrier mechanics
- ⬜ Demolition Derby game mode — no checkpoints, elimination by lives
- ⬜ Free for All game mode — personal flags, point scoring

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
- ✅ Activation WebSocket protocol — `programming_timer`, `your_program`, per–sub-step `register_events` with `substep_id` / `substep_index` / `substep_total`
- ✅ Map selection — `GET /boards`, host `set_board` in lobby, `board_id` on `create_room`, `game_started` / `state_sync` carry full board JSON; 3D uses server board after start
- ✅ Laser beam playback — red additive beam along `laser_path` during activation lasers sub-step (fade + store-driven)

---

## BUGS

- (none open)
