from __future__ import annotations

from game.board import Board
from game.cards import Card
from game.activation import ActivationEvent
from game.engine import GameEngine, GamePhase


MAX_PLAYERS = 4


class RoomError(Exception):
    pass


class Room:
    def __init__(self, room_id: str, board: Board) -> None:
        self.room_id = room_id
        self.engine = GameEngine(board)

    def join(self, player_id: str) -> None:
        if player_id in self.engine.robots:
            return  # reconnect — robot already exists
        if self.engine.phase != GamePhase.LOBBY:
            # Allow reconnect only; new players not accepted mid-game
            raise RoomError("Game already in progress")
        if len(self.engine.robots) >= MAX_PLAYERS:
            raise RoomError("Room is full")
        self.engine.add_player(player_id)

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
