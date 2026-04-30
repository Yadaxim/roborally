from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Direction(Enum):
    NORTH = "north"
    EAST = "east"
    SOUTH = "south"
    WEST = "west"


class TileType(Enum):
    FLOOR = "floor"
    CONVEYOR = "conveyor"
    GEAR = "gear"
    PIT = "pit"
    REPAIR = "repair"
    DOUBLE_REPAIR = "double_repair"
    LASER_EMITTER = "laser_emitter"
    CHECKPOINT = "checkpoint"
    PUSHER = "pusher"


_TURN_LEFT: dict[Direction, Direction] = {
    Direction.NORTH: Direction.WEST,
    Direction.WEST: Direction.SOUTH,
    Direction.SOUTH: Direction.EAST,
    Direction.EAST: Direction.NORTH,
}

_TURN_RIGHT: dict[Direction, Direction] = {v: k for k, v in _TURN_LEFT.items()}

_OPPOSITE: dict[Direction, Direction] = {
    Direction.NORTH: Direction.SOUTH,
    Direction.SOUTH: Direction.NORTH,
    Direction.EAST: Direction.WEST,
    Direction.WEST: Direction.EAST,
}

_DELTA: dict[Direction, tuple[int, int]] = {
    Direction.NORTH: (0, -1),
    Direction.SOUTH: (0, 1),
    Direction.EAST: (1, 0),
    Direction.WEST: (-1, 0),
}


def turn_left(d: Direction) -> Direction:
    return _TURN_LEFT[d]


def turn_right(d: Direction) -> Direction:
    return _TURN_RIGHT[d]


def opposite(d: Direction) -> Direction:
    return _OPPOSITE[d]


def delta(d: Direction) -> tuple[int, int]:
    return _DELTA[d]


@dataclass
class Tile:
    type: TileType = TileType.FLOOR
    walls: set[Direction] = field(default_factory=set)
    direction: Direction | None = None       # conveyor/pusher/laser direction
    rotation: str | None = None             # "clockwise" | "counter_clockwise" for gears
    speed: int = 1                          # conveyor speed (1=green, 2=express/blue)
    checkpoint_num: int | None = None
    laser_count: int = 1
    active_registers: list[int] = field(default_factory=list)  # pusher schedule


@dataclass
class Board:
    width: int
    height: int
    _tiles: list[list[Tile]]
    start_positions: list[tuple[int, int]]
    checkpoints: list[tuple[int, int]]      # ordered list of (x, y)

    # ------------------------------------------------------------------
    # Factory methods
    # ------------------------------------------------------------------

    @classmethod
    def empty(cls, width: int, height: int) -> Board:
        tiles = [[Tile() for _ in range(width)] for _ in range(height)]
        return cls(width=width, height=height, _tiles=tiles,
                   start_positions=[], checkpoints=[])

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Board:
        width, height = data["width"], data["height"]
        board = cls.empty(width, height)
        board.start_positions = [tuple(p) for p in data.get("start_positions", [])]
        board.checkpoints = [tuple(p) for p in data.get("checkpoints", [])]

        for td in data.get("tiles", []):
            x, y = td["x"], td["y"]
            tile = board.tile_at(x, y)
            tile.type = TileType(td["type"])
            tile.walls = {Direction(w) for w in td.get("walls", [])}
            if "direction" in td:
                tile.direction = Direction(td["direction"])
            if "rotation" in td:
                tile.rotation = td["rotation"]
            if "speed" in td:
                tile.speed = td["speed"]
            if "checkpoint_num" in td:
                tile.checkpoint_num = td["checkpoint_num"]
            if "laser_count" in td:
                tile.laser_count = td["laser_count"]
            if "active_registers" in td:
                tile.active_registers = td["active_registers"]

        return board

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def tile_at(self, x: int, y: int) -> Tile:
        return self._tiles[y][x]

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def neighbour(self, x: int, y: int, d: Direction) -> tuple[int, int] | None:
        dx, dy = delta(d)
        nx, ny = x + dx, y + dy
        return (nx, ny) if self.in_bounds(nx, ny) else None

    def can_move(self, x: int, y: int, d: Direction) -> bool:
        """True if a robot at (x,y) can move one step in direction d (walls only, ignores robots)."""
        if d in self.tile_at(x, y).walls:
            return False
        dest = self.neighbour(x, y, d)
        if dest is None:
            return False
        if opposite(d) in self.tile_at(*dest).walls:
            return False
        return True
