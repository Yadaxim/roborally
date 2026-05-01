from __future__ import annotations

from game.board import Board, Direction, TileType, opposite, turn_left, turn_right
from game.robot import Robot


def _conveyor_rotation(entry_dir: Direction, exit_dir: Direction) -> str | None:
    """Return 'left', 'right', or None depending on how the belt turns.

    entry_dir: the side of the tile the robot entered FROM (opposite of travel direction).
    exit_dir:  the direction the belt pushes the robot toward.
    """
    travel_dir = opposite(entry_dir)
    if exit_dir == turn_right(travel_dir):
        return "right"
    if exit_dir == turn_left(travel_dir):
        return "left"
    return None


def apply_conveyors(
    board: Board,
    robots: list[Robot],
    express_only: bool,
) -> None:
    """Move all robots that are currently on a conveyor tile one step.

    express_only=True  → only robots on speed-2 (express/blue) tiles move.
    express_only=False → all conveyor robots move (speed 1 and 2).

    Call sequence per register:
        apply_conveyors(..., express_only=True)   # sub-step b
        apply_conveyors(..., express_only=False)  # sub-step c

    Walls block the move; off-board or pit landing destroys the robot.
    """
    robot_positions: dict[tuple[int, int], Robot] = {(r.x, r.y): r for r in robots}

    eligible: list[Robot] = []
    for robot in robots:
        if not robot.is_alive:
            continue
        tile = board.tile_at(robot.x, robot.y)
        if tile.type != TileType.CONVEYOR:
            continue
        if express_only and tile.speed < 2:
            continue
        eligible.append(robot)

    for robot in eligible:
        if not robot.is_alive:
            continue
        tile = board.tile_at(robot.x, robot.y)
        exit_dir = tile.direction

        if not board.can_move(robot.x, robot.y, exit_dir):
            dest = board.neighbour(robot.x, robot.y, exit_dir)
            if dest is None:
                robot._destroy()
            continue

        dest = board.neighbour(robot.x, robot.y, exit_dir)
        if dest is None:
            robot._destroy()
            continue

        # If destination is occupied and that robot is also blocked, stay
        occupant = robot_positions.get(dest)
        if occupant is not None and occupant.is_alive:
            if not board.can_move(occupant.x, occupant.y, exit_dir):
                continue

        # Determine rotation: compare entry direction with exit direction
        stored_entry = getattr(tile, "_entry_direction", None)
        entry_dir = stored_entry if stored_entry is not None else opposite(exit_dir)
        rotation = _conveyor_rotation(entry_dir, exit_dir)

        del robot_positions[(robot.x, robot.y)]
        robot.x, robot.y = dest
        robot_positions[(robot.x, robot.y)] = robot

        if rotation == "right":
            robot.rotate_right()
        elif rotation == "left":
            robot.rotate_left()

        if not board.in_bounds(robot.x, robot.y):
            robot._destroy()
        elif board.tile_at(robot.x, robot.y).type == TileType.PIT:
            robot._destroy()
