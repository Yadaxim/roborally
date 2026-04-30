from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from game.board import Board, Direction, opposite, turn_left, turn_right

if TYPE_CHECKING:
    pass

MAX_DAMAGE = 10   # 10th point destroys the robot
STARTING_LIVES = 3
MAX_HAND = 9
# Registers lock from 5 backward when damage exceeds 4
# damage 5 → lock reg 5; damage 6 → lock 5,4; ... damage 9 → lock 5,4,3,2,1
_LOCK_THRESHOLD = 4


@dataclass
class Robot:
    id: str
    x: int
    y: int
    facing: Direction
    damage: int = 0
    lives: int = STARTING_LIVES
    archive: tuple[int, int] = field(init=False)
    _alive: bool = field(default=True, init=False)

    def __post_init__(self) -> None:
        self.archive = (self.x, self.y)

    # ------------------------------------------------------------------
    # State queries
    # ------------------------------------------------------------------

    @property
    def is_alive(self) -> bool:
        return self._alive and self.lives > 0

    @property
    def hand_size(self) -> int:
        return max(0, MAX_HAND - self.damage)

    @property
    def locked_registers(self) -> set[int]:
        """Register numbers (1–5) that are locked due to damage."""
        locked = set()
        excess = self.damage - _LOCK_THRESHOLD
        for i in range(excess):
            reg = 5 - i
            if reg >= 1:
                locked.add(reg)
        return locked

    # ------------------------------------------------------------------
    # Rotation
    # ------------------------------------------------------------------

    def rotate_left(self) -> None:
        self.facing = turn_left(self.facing)

    def rotate_right(self) -> None:
        self.facing = turn_right(self.facing)

    def rotate_180(self) -> None:
        self.facing = opposite(self.facing)

    # ------------------------------------------------------------------
    # Movement
    # ------------------------------------------------------------------

    def move_forward(self, board: Board, steps: int) -> None:
        for _ in range(steps):
            if not board.can_move(self.x, self.y, self.facing):
                dest = board.neighbour(self.x, self.y, self.facing)
                if dest is None:
                    self._destroy()
                return
            dest = board.neighbour(self.x, self.y, self.facing)
            if dest is None:
                self._destroy()
                return
            self.x, self.y = dest

    def move_backward(self, board: Board) -> None:
        backward = opposite(self.facing)
        if not board.can_move(self.x, self.y, backward):
            dest = board.neighbour(self.x, self.y, backward)
            if dest is None:
                self._destroy()
            return
        dest = board.neighbour(self.x, self.y, backward)
        if dest is None:
            self._destroy()
            return
        self.x, self.y = dest

    # ------------------------------------------------------------------
    # Damage & destruction
    # ------------------------------------------------------------------

    def take_damage(self, amount: int) -> None:
        self.damage = min(self.damage + amount, MAX_DAMAGE)
        if self.damage >= MAX_DAMAGE:
            self._destroy()

    def _destroy(self) -> None:
        self._alive = False

    # ------------------------------------------------------------------
    # Archive & respawn
    # ------------------------------------------------------------------

    def update_archive(self, x: int, y: int) -> None:
        self.archive = (x, y)

    def respawn(self) -> None:
        """Respawn at archive with 2 damage, costs one life."""
        if self.lives <= 0:
            return
        self.lives -= 1
        if self.lives == 0:
            self._alive = False
            return
        self.x, self.y = self.archive
        self.damage = 2
        self._alive = True
