from __future__ import annotations

from game.board import Board, Direction, TileType, opposite
from game.robot import Robot


def _wall_blocks(board: Board, x: int, y: int, direction: Direction) -> bool:
    """True if a wall (not the board edge) blocks movement from (x,y) in direction."""
    if direction in board.tile_at(x, y).walls:
        return True
    dest = board.neighbour(x, y, direction)
    if dest is not None and opposite(direction) in board.tile_at(*dest).walls:
        return True
    return False


def push_robots(
    board: Board,
    robots: list[Robot],
    pusher_x: int,
    pusher_y: int,
    direction: Direction,
) -> list[str]:
    """Push the robot at the cell adjacent to (pusher_x, pusher_y) in direction,
    chaining into any robots occupying subsequent squares.

    - Wall blocking: entire chain stays put, returns [].
    - Board edge: last robot in chain is destroyed, rest move, returns moved IDs.
    - Pit: robot is destroyed after landing.
    """
    robot_positions: dict[tuple[int, int], Robot] = {(r.x, r.y): r for r in robots}

    # Locate the first robot to push
    first_cell = board.neighbour(pusher_x, pusher_y, direction)
    if first_cell is None:
        return []
    first = robot_positions.get(first_cell)
    if first is None:
        return []

    # Gather contiguous chain of robots in the push direction
    chain: list[Robot] = []
    cx, cy = first_cell
    while True:
        robot = robot_positions.get((cx, cy))
        if robot is None:
            break
        chain.append(robot)
        nb = board.neighbour(cx, cy, direction)
        if nb is None:
            break
        cx, cy = nb

    # Check if the chain is wall-blocked (walls only, not board edge)
    last = chain[-1]
    if _wall_blocks(board, last.x, last.y, direction):
        return []

    # Move chain from the back forward
    moved: list[str] = []
    for robot in reversed(chain):
        dest = board.neighbour(robot.x, robot.y, direction)
        if dest is None:
            # Pushed off the board
            robot._destroy()
        else:
            robot.x, robot.y = dest
            if board.tile_at(robot.x, robot.y).type == TileType.PIT:
                robot._destroy()
        moved.append(robot.id)

    return moved
