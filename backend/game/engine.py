from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from game.activation import ActivationEvent, execute_register
from game.board import Board, Direction
from game.cards import Card, build_deck, deal
from game.robot import Robot


class GamePhase(Enum):
    LOBBY = "lobby"
    PROGRAMMING = "programming"
    ACTIVATION = "activation"
    GAME_OVER = "game_over"


@dataclass
class GameEngine:
    board: Board
    phase: GamePhase = GamePhase.LOBBY
    robots: dict[str, Robot] = field(default_factory=dict)
    hands: dict[str, list[Card]] = field(default_factory=dict)
    registers: dict[str, list[Card] | None] = field(default_factory=dict)
    locked_cards: dict[str, dict[int, Card]] = field(default_factory=dict)  # pid → {reg_num_1based → Card}
    current_register: int = 1
    winner: str | None = None
    _deck: list[Card] = field(default_factory=build_deck)
    _start_index: int = 0

    def add_player(self, player_id: str) -> None:
        if self.phase != GamePhase.LOBBY:
            raise RuntimeError("Cannot add players outside lobby phase")
        idx = self._start_index
        self._start_index += 1
        if idx < len(self.board.start_positions):
            x, y = self.board.start_positions[idx]
        else:
            x, y = idx, 0
        self.robots[player_id] = Robot(id=player_id, x=x, y=y, facing=Direction.NORTH)
        self.hands[player_id] = []
        self.registers[player_id] = None
        self.locked_cards[player_id] = {}

    def start_game(self) -> None:
        if not self.robots:
            raise RuntimeError("Need at least one player to start")
        self.phase = GamePhase.PROGRAMMING
        self._deal_hands()

    def _deal_hands(self) -> None:
        import random
        deck = build_deck()
        random.shuffle(deck)
        for pid, robot in self.robots.items():
            if robot.is_alive:
                self.hands[pid] = deal(deck, robot.damage)

    def submit_registers(self, player_id: str, cards: list[Card]) -> None:
        if self.phase != GamePhase.PROGRAMMING:
            raise RuntimeError("Not in programming phase")
        if len(cards) != 5:
            raise ValueError("Must submit exactly 5 cards")
        robot = self.robots[player_id]
        locked_regs = robot.locked_registers
        locked = self.locked_cards.get(player_id, {})
        hand_remaining = list(self.hands[player_id])
        for i, card in enumerate(cards):
            reg_num = i + 1  # 1-based register number
            if reg_num in locked_regs:
                expected = locked.get(reg_num)
                if expected is not None and card != expected:
                    raise ValueError(f"Register {reg_num} is locked — must use the retained card")
            else:
                if card not in hand_remaining:
                    raise ValueError(f"Card {card} not in hand")
                hand_remaining.remove(card)
        self.registers[player_id] = list(cards)
        if all(v is not None for v in self.registers.values()):
            self.phase = GamePhase.ACTIVATION
            self.current_register = 1

    def execute_next_register(self) -> list[ActivationEvent]:
        if self.phase != GamePhase.ACTIVATION:
            raise RuntimeError("Not in activation phase")
        reg = self.current_register
        card_assignments: dict[str, Card] = {}
        for pid, regs in self.registers.items():
            if regs is not None and len(regs) >= reg:
                card_assignments[pid] = regs[reg - 1]
        robots = list(self.robots.values())
        events = execute_register(self.board, robots, card_assignments, reg)
        self._check_win_condition()
        if self.phase == GamePhase.GAME_OVER:
            return events
        self.current_register += 1
        if self.current_register > 5:
            for pid, robot in self.robots.items():
                locked_regs = robot.locked_registers
                regs = self.registers.get(pid)
                if locked_regs and regs is not None:
                    self.locked_cards[pid] = {
                        reg: regs[reg - 1] for reg in locked_regs if len(regs) >= reg
                    }
                else:
                    self.locked_cards[pid] = {}
            for robot in self.robots.values():
                if not robot._alive:
                    robot.respawn()
            self.phase = GamePhase.PROGRAMMING
            self.current_register = 1
            for pid in self.registers:
                self.registers[pid] = None
            self._deal_hands()
        return events

    def _check_win_condition(self) -> None:
        total_checkpoints = len(self.board.checkpoints)
        for pid, robot in self.robots.items():
            if total_checkpoints > 0 and robot.is_alive and robot.checkpoints_touched >= total_checkpoints:
                self.winner = pid
                self.phase = GamePhase.GAME_OVER
                return
        # Only end from elimination when every robot is permanently out of lives
        if self.robots and all(r.lives <= 0 for r in self.robots.values()):
            self.phase = GamePhase.GAME_OVER
