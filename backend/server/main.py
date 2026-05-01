from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from game.board import Board
from game.engine import GamePhase
from game.robot import Robot
from server.rooms import Room, RoomError
from server.schemas import (
    CardOut,
    CmdJoin,
    CmdStart,
    CmdSubmitRegisters,
    EventOut,
    MsgDealHand,
    MsgError,
    MsgGameOver,
    MsgGameStarted,
    MsgJoined,
    MsgPhaseChange,
    MsgRegisterEvents,
    RobotOut,
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

PROGRAMMING_TIMEOUT = 30  # seconds


def _load_board(board_name: str) -> Board:
    import json as _json
    import pathlib
    path = pathlib.Path(__file__).parent.parent / "data" / "boards" / f"{board_name}.json"
    if path.exists():
        return Board.from_dict(_json.loads(path.read_text()))
    # Fallback: empty 12x12 for development, robots start in the middle
    board = Board.empty(12, 12)
    board.start_positions = [(2 + i * 2, 6) for i in range(4)]
    return board


def _robot_out(r: Robot) -> RobotOut:
    return RobotOut(
        id=r.id, x=r.x, y=r.y, facing=r.facing.value,
        damage=r.damage, lives=r.lives,
        checkpoints_touched=r.checkpoints_touched,
        is_alive=r.is_alive,
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
        await asyncio.sleep(0.1)  # small gap between registers for client animation

    if room.engine.phase == GamePhase.GAME_OVER:
        await _broadcast(room_id, MsgGameOver(winner=room.engine.winner))
        return

    # Back to programming — deal new hands
    await _deal_hands(room_id)


async def _deal_hands(room_id: str) -> None:
    room = _rooms[room_id]
    await _broadcast(room_id, MsgPhaseChange(phase="programming"))
    conns = _connections.get(room_id, {})
    for pid, ws in list(conns.items()):
        hand = room.get_hand(pid)
        try:
            await _send(ws, MsgDealHand(hand=[CardOut.from_card(c) for c in hand]))
        except Exception:
            pass


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    room_id: str | None = None
    player_id: str | None = None

    try:
        # First message must be "join"
        raw = await ws.receive_text()
        data = json.loads(raw)
        cmd = CmdJoin(**data)
        room_id = cmd.room_id
        player_id = cmd.player_id

        if room_id not in _rooms:
            board = _load_board("dizzy_highway")
            _rooms[room_id] = Room(room_id, board)
            _connections[room_id] = {}

        room = _rooms[room_id]
        try:
            room.join(player_id)
        except RoomError as e:
            await _send(ws, MsgError(message=str(e)))
            await ws.close()
            return

        _connections[room_id][player_id] = ws
        await _send(ws, MsgJoined(player_id=player_id, room_id=room_id))

        # Main message loop
        async for raw in ws.iter_text():
            data = json.loads(raw)
            msg_type = data.get("type")

            if msg_type == "start":
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
