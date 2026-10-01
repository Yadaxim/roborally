from __future__ import annotations

from typing import Any

from game.board import Board
from game.cards import Card
from game.activation import ActivationEvent
from game.engine import GameEngine, GamePhase


MAX_PLAYERS = 4
MIN_PLAYERS_TO_FORCE_START = 1


class RoomError(Exception):
    pass


class Room:
    def __init__(
        self,
        room_id: str,
        board: Board,
        board_id: str,
        board_dict: dict[str, Any],
        room_name: str = "",
        host_id: str = "",
        required_players: int = 2,
        game_mode: str = "standard",
    ) -> None:
        self.room_id = room_id
        self.room_name = room_name or room_id
        self.host_id = host_id
        self.required_players = required_players
        self.board_id = board_id
        self.board_dict = board_dict
        self.engine = GameEngine(board)
        self.ready: dict[str, bool] = {}
        self.paused: bool = False
        self.game_mode: str = game_mode

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
        return len(self.engine.robots) >= MIN_PLAYERS_TO_FORCE_START

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

    def run_next_activation_substep(self) -> tuple[int, str, int, list[ActivationEvent]]:
        try:
            return self.engine.execute_next_substep()
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
            "board_id": self.board_id,
            "board_name": self.board_dict.get("name", self.board_id),
            "game_mode": self.game_mode,
        }

    def replace_lobby_board(self, board: Board, board_id: str, board_dict: dict[str, Any]) -> None:
        """Swap factory board in lobby; robots re-seated on new start positions; ready flags cleared."""
        if self.engine.phase != GamePhase.LOBBY:
            raise RoomError("Can only change board in lobby")
        player_ids = list(self.engine.robots.keys())
        self.board_id = board_id
        self.board_dict = board_dict
        self.engine = GameEngine(board)
        self.ready = {}
        for pid in player_ids:
            self.engine.add_player(pid)
            self.ready[pid] = False
