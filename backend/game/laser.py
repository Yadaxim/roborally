from __future__ import annotations

from dataclasses import dataclass, field

from game.board import Board, Direction, opposite
from game.robot import Robot


@dataclass
class LaserResult:
    path: list[tuple[int, int]]        # cells the beam passed through (excluding start)
    hit_robot_id: str | None = None    # ID of the first robot hit, or None


def fire_laser(
    board: Board,
    robots: list[Robot],
    x: int,
    y: int,
    direction: Direction,
    count: int = 1,
) -> LaserResult:
    """Trace a laser beam from (x, y) in direction, dealing `count` damage to
    the first robot it hits. Returns the traversed path and the hit robot ID.

    The cell (x, y) is the emitter — any robot there is not targeted.
    """
    robot_positions: dict[tuple[int, int], Robot] = {
        (r.x, r.y): r for r in robots
    }

    path: list[tuple[int, int]] = []
    cx, cy = x, y

    while True:
        # Check if beam can leave current cell
        if direction in board.tile_at(cx, cy).walls:
            break

        dest = board.neighbour(cx, cy, direction)
        if dest is None:
            break

        nx, ny = dest

        # Check if beam can enter next cell
        if opposite(direction) in board.tile_at(nx, ny).walls:
            break

        path.append((nx, ny))
        cx, cy = nx, ny

        # Check if a robot is here (blocks and receives damage)
        robot = robot_positions.get((cx, cy))
        if robot is not None:
            robot.take_damage(count)
            return LaserResult(path=path, hit_robot_id=robot.id)

    return LaserResult(path=path, hit_robot_id=None)
