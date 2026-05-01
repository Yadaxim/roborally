from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

from game.activation import ActivationEvent
from game.board import Direction
from game.cards import Card, CardType


# ── Outbound (server → client) ──────────────────────────────────────────────

class CardOut(BaseModel):
    type: str
    priority: int

    @classmethod
    def from_card(cls, card: Card) -> CardOut:
        return cls(type=card.type.value, priority=card.priority)


class RobotOut(BaseModel):
    id: str
    x: int
    y: int
    facing: str
    damage: int
    lives: int
    checkpoints_touched: int
    is_alive: bool


class EventOut(BaseModel):
    type: str
    robot_id: str = ""
    from_pos: tuple[int, int] | None = None
    to: tuple[int, int] | None = None
    from_dir: str | None = None
    to_dir: str | None = None
    amount: int = 0
    laser_path: list[tuple[int, int]] = []
    checkpoint_num: int = 0

    @classmethod
    def from_event(cls, ev: ActivationEvent) -> EventOut:
        return cls(
            type=ev.type,
            robot_id=ev.robot_id,
            from_pos=ev.from_pos,
            to=ev.to,
            from_dir=ev.from_dir.value if ev.from_dir else None,
            to_dir=ev.to_dir.value if ev.to_dir else None,
            amount=ev.amount,
            laser_path=ev.laser_path,
            checkpoint_num=ev.checkpoint_num,
        )


class MsgJoined(BaseModel):
    type: Literal["joined"] = "joined"
    player_id: str
    room_id: str


class MsgGameStarted(BaseModel):
    type: Literal["game_started"] = "game_started"
    robots: list[RobotOut]


class MsgDealHand(BaseModel):
    type: Literal["deal_hand"] = "deal_hand"
    hand: list[CardOut]


class MsgPhaseChange(BaseModel):
    type: Literal["phase_change"] = "phase_change"
    phase: str


class MsgRegisterEvents(BaseModel):
    type: Literal["register_events"] = "register_events"
    register_num: int
    events: list[EventOut]
    robots: list[RobotOut]


class MsgGameOver(BaseModel):
    type: Literal["game_over"] = "game_over"
    winner: str | None


class MsgStateSync(BaseModel):
    type: Literal["state_sync"] = "state_sync"
    phase: str
    robots: list[RobotOut]
    hand: list[CardOut]  # empty outside programming phase or if player has no hand


class MsgError(BaseModel):
    type: Literal["error"] = "error"
    message: str


# ── Inbound (client → server) ────────────────────────────────────────────────

class CmdJoin(BaseModel):
    type: Literal["join"]
    room_id: str
    player_id: str


class CmdStart(BaseModel):
    type: Literal["start"]


class CmdSubmitRegisters(BaseModel):
    type: Literal["submit_registers"]
    cards: list[CardOut]


def parse_card(raw: CardOut) -> Card:
    return Card(type=CardType(raw.type), priority=raw.priority)
