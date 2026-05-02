from __future__ import annotations

from game.board import Board
from game.cards import Card
from game.activation import ActivationEvent
from game.engine import GameEngine, GamePhase


MAX_PLAYERS = 4
MIN_PLAYERS_TO_START = 2


class RoomError(Exception):
    pass


class Room:
    def __init__(
        self,
        room_id: str,
        board: Board,
        room_name: str = "",
        host_id: str = "",
        required_players: int = 2,
    ) -> None:
        self.room_id = room_id
        self.room_name = room_name or room_id
        self.host_id = host_id
        self.required_players = required_players
        self.engine = GameEngine(board)
        self.ready: dict[str, bool] = {}

    def join(self, player_id: str) -> None:
        if player_id in self.engine.robots:
            return  # reconnect — robot already exists
        if self.engine.phase != GamePhase.LOBBY:
            raise RoomError("Game already in progress")
        if len(self.engine.robots) >= MAX_PLAYERS:
            raise RoomError("Room is full")
        self.engine.add_player(player_id)
        self.ready[player_id] = False
        if not self.host_id:
            self.host_id = player_id

    def set_ready(self, player_id: str, value: bool) -> None:
        if player_id not in self.ready:
            raise RoomError("Player not in room")
        self.ready[player_id] = value

    @property
    def all_ready(self) -> bool:
        if len(self.ready) < self.required_players:
            return False
        return bool(self.ready) and all(self.ready.values())

    @property
    def can_force_start(self) -> bool:
        return len(self.engine.robots) >= MIN_PLAYERS_TO_START

    def start(self) -> None:
        try:
            self.engine.start_game()
        except RuntimeError as e:
            raise RoomError(str(e)) from e

    def get_hand(self, player_id: str) -> list[Card]:
        return list(self.engine.hands.get(player_id, []))

    def submit_registers(self, player_id: str, cards: list[Card]) -> None:
        try:
            self.engine.submit_registers(player_id, cards)
        except (RuntimeError, ValueError) as e:
            raise RoomError(str(e)) from e

    def run_next_register(self) -> list[ActivationEvent]:
        try:
            return self.engine.execute_next_register()
        except RuntimeError as e:
            raise RoomError(str(e)) from e

    def to_summary(self) -> dict:
        return {
            "room_id": self.room_id,
            "room_name": self.room_name,
            "host_id": self.host_id,
            "player_count": len(self.engine.robots),
            "required_players": self.required_players,
            "in_progress": self.engine.phase != GamePhase.LOBBY,
        }
