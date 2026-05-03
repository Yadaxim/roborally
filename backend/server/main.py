from __future__ import annotations

import asyncio
import json
import random
import string
import time
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from game.board import Board
from game.activation import REGISTER_SUBSTEPS
from game.cards import Card
from game.engine import GamePhase
from game.robot import Robot
from server.rooms import Room, RoomError
from server.schemas import (
    CardOut,
    CmdCreateRoom,
    CmdForceStart,
    CmdJoin,
    CmdJoinRoom,
    CmdReady,
    CmdSetPaused,
    CmdSubmitRegisters,
    EventOut,
    MsgDealHand,
    MsgProgrammingTimer,
    MsgYourProgram,
    MsgGamePaused,
    MsgError,
    MsgGameOver,
    MsgGameStarted,
    MsgJoined,
    MsgPhaseChange,
    MsgPlayerReady,
    MsgRegisterEvents,
    MsgRoomList,
    MsgRosterUpdate,
    MsgStateSync,
    PlayerInRoomOut,
    RobotOut,
    RoomSummary,
    parse_card,
)

app = FastAPI(title="RoboRally")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# room_id → Room
_rooms: dict[str, Room] = {}

# room_id → {player_id → WebSocket}
_connections: dict[str, dict[str, WebSocket]] = {}

# room_id → running timer task
_timers: dict[str, asyncio.Task] = {}

# programming timer: monotonic deadline and frozen remaining while paused
_programming_deadline_mono: dict[str, float] = {}
_programming_frozen_remaining: dict[str, float] = {}

# Clients connected but still choosing a room (awaiting first join/create/join_room message)
_browse_waiters: dict[int, WebSocket] = {}

PROGRAMMING_TIMEOUT = 30  # seconds


def _random_program_from_hand(room: Room, player_id: str) -> list[Card] | None:
    """Locked registers use retained cards; other registers get random cards from the remaining hand."""
    hand = list(room.get_hand(player_id))
    eng = room.engine
    robot = eng.robots[player_id]
    locked_regs = sorted(robot.locked_registers)
    locked_map = eng.locked_cards.get(player_id, {})
    program: list[Card | None] = [None] * 5

    for reg_num in locked_regs:
        if reg_num not in locked_map:
            return None
        c = locked_map[reg_num]
        program[reg_num - 1] = c
        try:
            idx = next(i for i, h in enumerate(hand) if h == c)
        except StopIteration:
            return None
        hand.pop(idx)

    open_slots = [i for i in range(5) if program[i] is None]
    need = len(open_slots)
    if len(hand) < need:
        return None
    random.shuffle(hand)
    pool = hand[:need]
    for slot, card in zip(open_slots, pool):
        program[slot] = card
    return [program[i] for i in range(5)]  # type: ignore[misc]


async def _send_your_program_to_all(room_id: str) -> None:
    room = _rooms.get(room_id)
    if room is None:
        return
    for _pid, ws in list(_connections.get(room_id, {}).items()):
        regs = room.engine.registers.get(_pid)
        if regs is None:
            continue
        try:
            await _send(ws, MsgYourProgram(cards=[CardOut.from_card(c) for c in regs]))
        except Exception:
            pass


async def _maybe_start_programming_timer(room_id: str) -> None:
    """Start the 30s countdown once the first player has committed (some but not all players done)."""
    room = _rooms.get(room_id)
    if room is None or room.engine.phase != GamePhase.PROGRAMMING:
        return
    if room_id in _programming_deadline_mono:
        return
    regs = room.engine.registers
    if not any(v is not None for v in regs.values()):
        return
    if all(v is not None for v in regs.values()):
        return
    _programming_deadline_mono[room_id] = time.monotonic() + PROGRAMMING_TIMEOUT
    rem_init = max(0.0, _programming_deadline_mono[room_id] - time.monotonic())
    await _broadcast(room_id, MsgProgrammingTimer(programming_seconds_remaining=rem_init))
    existing = _timers.get(room_id)
    if existing is not None and not existing.done():
        return
    _timers[room_id] = asyncio.create_task(_programming_timer(room_id))


def _load_board(board_name: str) -> Board:
    import json as _json
    import pathlib
    path = pathlib.Path(__file__).parent.parent / "data" / "boards" / f"{board_name}.json"
    if path.exists():
        return Board.from_dict(_json.loads(path.read_text()))
    # Fallback: empty 12x12 for development
    board = Board.empty(12, 12)
    board.start_positions = [(2 + i * 2, 6) for i in range(4)]
    return board


def _make_room_id() -> str:
    return "".join(random.choices(string.ascii_uppercase, k=4))


def _robot_out(r: Robot) -> RobotOut:
    return RobotOut(
        id=r.id, x=r.x, y=r.y, facing=r.facing.value,
        damage=r.damage, lives=r.lives,
        checkpoints_touched=r.checkpoints_touched,
        is_alive=r.is_alive,
        locked_registers=sorted(r.locked_registers),
    )


async def _send(ws: WebSocket, msg: Any) -> None:
    await ws.send_text(msg.model_dump_json())


async def _broadcast(room_id: str, msg: Any, exclude: str | None = None) -> None:
    conns = _connections.get(room_id, {})
    payload = msg.model_dump_json()
    for pid, ws in list(conns.items()):
        if pid != exclude:
            try:
                await ws.send_text(payload)
            except Exception:
                pass


def _room_list_msg() -> MsgRoomList:
    return MsgRoomList(rooms=[
        RoomSummary(**r.to_summary())
        for r in _rooms.values()
        if r.engine.phase == GamePhase.LOBBY
    ])


async def _broadcast_room_list_to_browsers() -> None:
    """Push fresh room_list to everyone still on the browse screen (no reload)."""
    if not _browse_waiters:
        return
    payload = _room_list_msg().model_dump_json()
    stale: list[int] = []
    for wid, bws in list(_browse_waiters.items()):
        try:
            await bws.send_text(payload)
        except Exception:
            stale.append(wid)
    for wid in stale:
        _browse_waiters.pop(wid, None)


def _roster_msg(room: Room) -> MsgRosterUpdate:
    return MsgRosterUpdate(players=[
        PlayerInRoomOut(
            player_id=pid,
            is_host=(pid == room.host_id),
            is_ready=room.ready.get(pid, False),
        )
        for pid in room.engine.robots
    ])


async def _broadcast_roster(room_id: str) -> None:
    await _broadcast(room_id, _roster_msg(_rooms[room_id]))


async def _wait_unpaused(room_id: str) -> None:
    while True:
        r = _rooms.get(room_id)
        if r is None or not r.paused:
            return
        await asyncio.sleep(0.15)


def _programming_seconds_remaining(room_id: str) -> float | None:
    room = _rooms.get(room_id)
    if room is None or room.engine.phase != GamePhase.PROGRAMMING:
        return None
    if room.paused:
        if room_id in _programming_frozen_remaining:
            return _programming_frozen_remaining[room_id]
        return None
    dl = _programming_deadline_mono.get(room_id)
    if dl is None:
        return None
    return max(0.0, dl - time.monotonic())


async def _run_activation(room_id: str) -> None:
    """Drive activation one rules sub-step at a time (8 substeps × 5 registers)."""
    room = _rooms[room_id]
    while room.engine.phase == GamePhase.ACTIVATION:
        await _wait_unpaused(room_id)
        room = _rooms.get(room_id)
        if room is None:
            break
        reg_num, sub_key, sub_idx, raw_events = room.run_next_activation_substep()
        robots = [_robot_out(r) for r in room.engine.robots.values()]
        msg = MsgRegisterEvents(
            register_num=reg_num,
            substep_id=sub_key,
            substep_index=sub_idx,
            substep_total=len(REGISTER_SUBSTEPS),
            events=[EventOut.from_event(e) for e in raw_events],
            robots=robots,
        )
        await _broadcast(room_id, msg)
        await asyncio.sleep(0.08)

    room = _rooms.get(room_id)
    if room is None:
        return
    if room.engine.phase == GamePhase.GAME_OVER:
        await _broadcast(room_id, MsgGameOver(winner=room.engine.winner))
        return

    await _deal_hands(room_id)


async def _programming_timer(room_id: str) -> None:
    """Auto-submit registers for players who haven't programmed when time runs out."""
    while True:
        room = _rooms.get(room_id)
        if room is None or room.engine.phase != GamePhase.PROGRAMMING:
            _programming_deadline_mono.pop(room_id, None)
            _programming_frozen_remaining.pop(room_id, None)
            return
        if room.paused:
            await asyncio.sleep(0.15)
            continue
        dl = _programming_deadline_mono.get(room_id)
        if dl is None:
            return
        now = time.monotonic()
        if now >= dl:
            break
        await asyncio.sleep(min(0.15, dl - now))

    room = _rooms.get(room_id)
    if room is None or room.engine.phase != GamePhase.PROGRAMMING:
        _programming_deadline_mono.pop(room_id, None)
        _programming_frozen_remaining.pop(room_id, None)
        return
    for pid, submitted in list(room.engine.registers.items()):
        if submitted is None:
            hand = room.get_hand(pid)
            if len(hand) >= 5:
                prog = _random_program_from_hand(room, pid)
                if prog is not None:
                    try:
                        room.submit_registers(pid, prog)
                    except RoomError:
                        pass
    _programming_deadline_mono.pop(room_id, None)
    _programming_frozen_remaining.pop(room_id, None)
    if room.engine.phase == GamePhase.ACTIVATION:
        await _send_your_program_to_all(room_id)
        await _broadcast(room_id, MsgPhaseChange(phase="activation"))
        asyncio.create_task(_run_activation(room_id))


async def _send_state_sync(ws: WebSocket, room: Room, player_id: str) -> None:
    phase = room.engine.phase.value
    robots = [_robot_out(r) for r in room.engine.robots.values()]
    hand: list[CardOut] = []
    locked_out: dict[int, CardOut] = {}
    if room.engine.phase == GamePhase.PROGRAMMING:
        hand = [CardOut.from_card(c) for c in room.get_hand(player_id)]
        raw_locked = room.engine.locked_cards.get(player_id, {})
        locked_out = {reg: CardOut.from_card(c) for reg, c in raw_locked.items()}
    rem = _programming_seconds_remaining(room.room_id) if room.engine.phase == GamePhase.PROGRAMMING else None
    await _send(ws, MsgStateSync(
        phase=phase, robots=robots, hand=hand, locked_cards=locked_out,
        paused=room.paused, programming_seconds_remaining=rem,
    ))


def _cancel_timer(room_id: str) -> None:
    task = _timers.pop(room_id, None)
    if task and not task.done():
        task.cancel()
    _programming_deadline_mono.pop(room_id, None)
    _programming_frozen_remaining.pop(room_id, None)


async def _deal_hands(room_id: str) -> None:
    room = _rooms[room_id]
    room.paused = False
    await _broadcast(room_id, MsgPhaseChange(phase="programming"))
    _cancel_timer(room_id)
    conns = _connections.get(room_id, {})
    for pid, ws in list(conns.items()):
        hand = room.get_hand(pid)
        locked = room.engine.locked_cards.get(pid, {})
        locked_out = {reg: CardOut.from_card(c) for reg, c in locked.items()}
        try:
            await _send(ws, MsgDealHand(
                hand=[CardOut.from_card(c) for c in hand],
                locked_cards=locked_out,
                programming_seconds_remaining=None,
            ))
        except Exception:
            pass


async def _start_game(room_id: str) -> None:
    room = _rooms[room_id]
    try:
        room.start()
    except RoomError as e:
        await _broadcast(room_id, MsgError(message=str(e)))
        return
    robots = [_robot_out(r) for r in room.engine.robots.values()]
    await _broadcast(room_id, MsgGameStarted(robots=robots))
    await _deal_hands(room_id)
    await _broadcast_room_list_to_browsers()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/rooms")
async def list_rooms() -> list[dict]:
    return [r.to_summary() for r in _rooms.values() if r.engine.phase == GamePhase.LOBBY]


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    room_id: str | None = None
    player_id: str | None = None

    try:
        # Send current room list to newly connected client
        await _send(ws, _room_list_msg())
        _browse_waiters[id(ws)] = ws

        # First message: join (legacy), create_room, or join_room
        raw = await ws.receive_text()
        data = json.loads(raw)
        msg_type = data.get("type")

        if msg_type == "join":
            # Legacy: room_id and player_id provided directly
            cmd = CmdJoin(**data)
            room_id = cmd.room_id
            player_id = cmd.player_id
            if room_id not in _rooms:
                board = _load_board("dizzy_highway")
                _rooms[room_id] = Room(room_id, board)
                _connections[room_id] = {}
            room = _rooms[room_id]
            is_reconnect = player_id in room.engine.robots
            try:
                room.join(player_id)
            except RoomError as e:
                await _send(ws, MsgError(message=str(e)))
                await ws.close()
                return
            _browse_waiters.pop(id(ws), None)
            _connections[room_id][player_id] = ws
            await _send(ws, MsgJoined(
                player_id=player_id,
                room_id=room_id,
                room_name=room.room_name,
                is_host=(room.host_id == player_id),
                required_players=room.required_players,
            ))
            if is_reconnect:
                await _send_state_sync(ws, room, player_id)
            await _broadcast_room_list_to_browsers()

        elif msg_type == "create_room":
            cmd = CmdCreateRoom(**data)
            player_id = cmd.player_name
            room_id = _make_room_id()
            while room_id in _rooms:
                room_id = _make_room_id()
            board = _load_board("dizzy_highway")
            _rooms[room_id] = Room(
                room_id, board,
                room_name=cmd.room_name,
                required_players=cmd.required_players,
            )
            _connections[room_id] = {}
            _rooms[room_id].join(player_id)
            _connections[room_id][player_id] = ws
            room = _rooms[room_id]
            _browse_waiters.pop(id(ws), None)
            await _send(ws, MsgJoined(
                player_id=player_id,
                room_id=room_id,
                room_name=cmd.room_name,
                is_host=True,
                required_players=cmd.required_players,
            ))
            await _broadcast_roster(room_id)
            await _broadcast_room_list_to_browsers()

        elif msg_type == "join_room":
            cmd = CmdJoinRoom(**data)
            player_id = cmd.player_name
            room_id = cmd.room_id
            if room_id not in _rooms:
                await _send(ws, MsgError(message="Room not found"))
                await ws.close()
                return
            room = _rooms[room_id]
            is_reconnect = player_id in room.engine.robots
            try:
                room.join(player_id)
            except RoomError as e:
                await _send(ws, MsgError(message=str(e)))
                await ws.close()
                return
            _connections[room_id][player_id] = ws
            _browse_waiters.pop(id(ws), None)
            await _send(ws, MsgJoined(
                player_id=player_id,
                room_id=room_id,
                room_name=room.room_name,
                is_host=(room.host_id == player_id),
                required_players=room.required_players,
            ))
            if is_reconnect:
                await _send_state_sync(ws, room, player_id)
            await _broadcast_roster(room_id)
            await _broadcast_room_list_to_browsers()

        else:
            await _send(ws, MsgError(message=f"Expected join, create_room, or join_room, got: {msg_type}"))
            await ws.close()
            return

        room = _rooms[room_id]

        # Main message loop
        async for raw in ws.iter_text():
            data = json.loads(raw)
            msg_type = data.get("type")

            if msg_type == "ready":
                cmd_r = CmdReady(**data)
                try:
                    room.set_ready(player_id, cmd_r.value)
                except RoomError as e:
                    await _send(ws, MsgError(message=str(e)))
                    continue
                await _broadcast(room_id, MsgPlayerReady(player_id=player_id, is_ready=cmd_r.value))
                if room.all_ready and room.engine.phase == GamePhase.LOBBY:
                    await _start_game(room_id)

            elif msg_type == "force_start":
                if player_id != room.host_id:
                    await _send(ws, MsgError(message="Only the host can force start"))
                    continue
                if not room.can_force_start:
                    await _send(ws, MsgError(message="Need at least one player to start"))
                    continue
                if room.engine.phase != GamePhase.LOBBY:
                    await _send(ws, MsgError(message="Game already started"))
                    continue
                await _start_game(room_id)

            elif msg_type == "start":
                # Legacy single-player start
                try:
                    room.start()
                    robots = [_robot_out(r) for r in room.engine.robots.values()]
                    await _broadcast(room_id, MsgGameStarted(robots=robots))
                    await _deal_hands(room_id)
                    await _broadcast_room_list_to_browsers()
                except RoomError as e:
                    await _send(ws, MsgError(message=str(e)))

            elif msg_type == "submit_registers":
                cmd_r = CmdSubmitRegisters(**data)
                cards = [parse_card(c) for c in cmd_r.cards]
                try:
                    room.submit_registers(player_id, cards)
                except RoomError as e:
                    await _send(ws, MsgError(message=str(e)))
                    continue
                if room.engine.phase == GamePhase.ACTIVATION:
                    _cancel_timer(room_id)
                    await _send_your_program_to_all(room_id)
                    await _broadcast(room_id, MsgPhaseChange(phase="activation"))
                    asyncio.create_task(_run_activation(room_id))
                else:
                    await _maybe_start_programming_timer(room_id)

            elif msg_type == "set_paused":
                cmd_p = CmdSetPaused(**data)
                if player_id != room.host_id:
                    await _send(ws, MsgError(message="Only the host can pause or resume"))
                    continue
                if room.engine.phase not in (GamePhase.PROGRAMMING, GamePhase.ACTIVATION):
                    await _send(ws, MsgError(message="Can only pause during programming or activation"))
                    continue
                if cmd_p.value:
                    if not room.paused:
                        dl = _programming_deadline_mono.get(room_id)
                        if dl is not None:
                            _programming_frozen_remaining[room_id] = max(0.0, dl - time.monotonic())
                        room.paused = True
                else:
                    if room.paused:
                        rem = _programming_frozen_remaining.pop(room_id, None)
                        room.paused = False
                        if rem is not None:
                            _programming_deadline_mono[room_id] = time.monotonic() + rem
                await _broadcast(room_id, MsgGamePaused(
                    paused=room.paused,
                    programming_seconds_remaining=_programming_seconds_remaining(room_id),
                ))

            else:
                await _send(ws, MsgError(message=f"Unknown command: {msg_type}"))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await _send(ws, MsgError(message=str(e)))
        except Exception:
            pass
    finally:
        _browse_waiters.pop(id(ws), None)
        if room_id and player_id:
            _connections.get(room_id, {}).pop(player_id, None)
            if room_id in _rooms and _rooms[room_id].engine.phase == GamePhase.LOBBY:
                if _connections.get(room_id):
                    await _broadcast_roster(room_id)
                await _broadcast_room_list_to_browsers()
