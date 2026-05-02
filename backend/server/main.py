from __future__ import annotations

import asyncio
import json
import random
import string
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from game.board import Board
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
    CmdSubmitRegisters,
    EventOut,
    MsgDealHand,
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

PROGRAMMING_TIMEOUT = 30  # seconds


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


async def _run_activation(room_id: str) -> None:
    """Drive all 5 registers, broadcasting events after each one."""
    room = _rooms[room_id]
    for reg in range(1, 6):
        if room.engine.phase != GamePhase.ACTIVATION:
            break
        events = room.run_next_register()
        robots = [_robot_out(r) for r in room.engine.robots.values()]
        msg = MsgRegisterEvents(
            register_num=reg,
            events=[EventOut.from_event(e) for e in events],
            robots=robots,
        )
        await _broadcast(room_id, msg)
        await asyncio.sleep(0.1)

    if room.engine.phase == GamePhase.GAME_OVER:
        await _broadcast(room_id, MsgGameOver(winner=room.engine.winner))
        return

    await _deal_hands(room_id)


async def _programming_timer(room_id: str) -> None:
    """Auto-submit registers for players who haven't programmed when time runs out."""
    await asyncio.sleep(PROGRAMMING_TIMEOUT)
    room = _rooms.get(room_id)
    if room is None or room.engine.phase != GamePhase.PROGRAMMING:
        return
    for pid, submitted in list(room.engine.registers.items()):
        if submitted is None:
            hand = room.get_hand(pid)
            if len(hand) >= 5:
                try:
                    room.submit_registers(pid, hand[:5])
                except RoomError:
                    pass
    if room.engine.phase == GamePhase.ACTIVATION:
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
    await _send(ws, MsgStateSync(phase=phase, robots=robots, hand=hand, locked_cards=locked_out))


def _cancel_timer(room_id: str) -> None:
    task = _timers.pop(room_id, None)
    if task and not task.done():
        task.cancel()


async def _deal_hands(room_id: str) -> None:
    room = _rooms[room_id]
    await _broadcast(room_id, MsgPhaseChange(phase="programming"))
    conns = _connections.get(room_id, {})
    for pid, ws in list(conns.items()):
        hand = room.get_hand(pid)
        locked = room.engine.locked_cards.get(pid, {})
        locked_out = {reg: CardOut.from_card(c) for reg, c in locked.items()}
        try:
            await _send(ws, MsgDealHand(hand=[CardOut.from_card(c) for c in hand], locked_cards=locked_out))
        except Exception:
            pass
    _cancel_timer(room_id)
    _timers[room_id] = asyncio.create_task(_programming_timer(room_id))


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
            await _send(ws, MsgJoined(
                player_id=player_id,
                room_id=room_id,
                room_name=cmd.room_name,
                is_host=True,
                required_players=cmd.required_players,
            ))
            await _broadcast_roster(room_id)

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
                    await _send(ws, MsgError(message="Need at least 2 players to start"))
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
                    await _broadcast(room_id, MsgPhaseChange(phase="activation"))
                    asyncio.create_task(_run_activation(room_id))

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
        if room_id and player_id:
            _connections.get(room_id, {}).pop(player_id, None)
            if room_id in _rooms and _rooms[room_id].engine.phase == GamePhase.LOBBY:
                if _connections.get(room_id):
                    await _broadcast_roster(room_id)
