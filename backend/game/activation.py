from __future__ import annotations

from dataclasses import dataclass, field

from game.board import Board, Direction, TileType, opposite
from game.cards import Card, CardType
from game.conveyor import apply_conveyors
from game.laser import fire_laser
from game.push import push_robots
from game.robot import Robot


@dataclass
class ActivationEvent:
    type: str           # "move" | "rotate" | "damage" | "destroy" | "laser" | "checkpoint"
    robot_id: str = ""
    from_pos: tuple[int, int] | None = None
    to: tuple[int, int] | None = None
    from_dir: Direction | None = None
    to_dir: Direction | None = None
    amount: int = 0
    laser_path: list[tuple[int, int]] = field(default_factory=list)
    checkpoint_num: int = 0


def _step_robot(
    board: Board,
    robot: Robot,
    direction: Direction,
    all_robots: list[Robot],
    events: list[ActivationEvent],
) -> None:
    """Move robot one step in direction, pushing any occupant. Emits events."""
    from_pos = (robot.x, robot.y)

    # Try to push the robot occupying the destination
    dest = board.neighbour(robot.x, robot.y, direction)
    if dest is not None:
        occupant_map = {(r.x, r.y): r for r in all_robots if r.is_alive and r is not robot}
        occupant = occupant_map.get(dest)
        if occupant is not None:
            prev_pos = (occupant.x, occupant.y)
            push_robots(board, all_robots, robot.x, robot.y, direction)
            if (occupant.x, occupant.y) != prev_pos or not occupant.is_alive:
                events.append(ActivationEvent(
                    type="move" if occupant.is_alive else "destroy",
                    robot_id=occupant.id,
                    from_pos=prev_pos,
                    to=(occupant.x, occupant.y) if occupant.is_alive else None,
                ))

    # Now move this robot
    if not board.can_move(robot.x, robot.y, direction):
        nb = board.neighbour(robot.x, robot.y, direction)
        if nb is None:
            robot._destroy()
            events.append(ActivationEvent(type="destroy", robot_id=robot.id, from_pos=from_pos))
        return

    nb = board.neighbour(robot.x, robot.y, direction)
    if nb is None:
        robot._destroy()
        events.append(ActivationEvent(type="destroy", robot_id=robot.id, from_pos=from_pos))
        return

    robot.x, robot.y = nb
    events.append(ActivationEvent(type="move", robot_id=robot.id, from_pos=from_pos, to=nb))

    if not board.in_bounds(robot.x, robot.y) or board.tile_at(robot.x, robot.y).type == TileType.PIT:
        robot._destroy()
        events.append(ActivationEvent(type="destroy", robot_id=robot.id))


def _apply_card(
    board: Board,
    robot: Robot,
    card: Card,
    all_robots: list[Robot],
    events: list[ActivationEvent],
) -> None:
    if card.type in (CardType.MOVE_1, CardType.MOVE_2, CardType.MOVE_3):
        steps = {CardType.MOVE_1: 1, CardType.MOVE_2: 2, CardType.MOVE_3: 3}[card.type]
        for _ in range(steps):
            if robot.is_alive:
                _step_robot(board, robot, robot.facing, all_robots, events)
    elif card.type == CardType.BACK_UP:
        if robot.is_alive:
            _step_robot(board, robot, opposite(robot.facing), all_robots, events)
    else:
        old_dir = robot.facing
        if card.type == CardType.TURN_LEFT:
            robot.rotate_left()
        elif card.type == CardType.TURN_RIGHT:
            robot.rotate_right()
        elif card.type == CardType.U_TURN:
            robot.rotate_180()
        events.append(ActivationEvent(
            type="rotate", robot_id=robot.id,
            from_dir=old_dir, to_dir=robot.facing,
        ))


def execute_register(
    board: Board,
    robots: list[Robot],
    card_assignments: dict[str, Card],
    register_num: int,
) -> list[ActivationEvent]:
    """Execute all 8 sub-steps for one register. Returns animation events."""
    events: list[ActivationEvent] = []

    # --- Sub-step 1: Cards in priority order ---
    alive = [r for r in robots if r.is_alive]
    ordered = sorted(
        [(r, card_assignments[r.id]) for r in alive if r.id in card_assignments],
        key=lambda x: x[1].priority,
        reverse=True,
    )
    for robot, card in ordered:
        if robot.is_alive:
            _apply_card(board, robot, card, robots, events)

    # --- Sub-steps 2+3: Conveyors ---
    alive = [r for r in robots if r.is_alive]
    apply_conveyors(board, alive, express_only=True)
    apply_conveyors(board, alive, express_only=False)

    # --- Sub-step 4: Push panels ---
    alive = [r for r in robots if r.is_alive]
    for y in range(board.height):
        for x in range(board.width):
            tile = board.tile_at(x, y)
            if tile.type == TileType.PUSHER and register_num in tile.active_registers:
                push_robots(board, alive, x, y, tile.direction)

    # --- Sub-step 5: Gears ---
    alive = [r for r in robots if r.is_alive]
    for robot in alive:
        tile = board.tile_at(robot.x, robot.y)
        if tile.type == TileType.GEAR:
            old_dir = robot.facing
            if tile.rotation == "clockwise":
                robot.rotate_right()
            else:
                robot.rotate_left()
            events.append(ActivationEvent(
                type="rotate", robot_id=robot.id,
                from_dir=old_dir, to_dir=robot.facing,
            ))

    # --- Sub-step 6: Crushers ---
    alive = [r for r in robots if r.is_alive]
    for y in range(board.height):
        for x in range(board.width):
            tile = board.tile_at(x, y)
            if tile.type == TileType.CRUSHER and register_num in tile.active_registers:
                for robot in alive:
                    if robot.x == x and robot.y == y:
                        robot._destroy()
                        events.append(ActivationEvent(type="destroy", robot_id=robot.id))

    # --- Sub-step 7: Lasers ---
    alive = [r for r in robots if r.is_alive]
    for y in range(board.height):
        for x in range(board.width):
            tile = board.tile_at(x, y)
            if tile.type == TileType.LASER_EMITTER and tile.direction:
                result = fire_laser(board, alive, x, y, tile.direction, tile.laser_count)
                if result.path:
                    events.append(ActivationEvent(
                        type="laser", laser_path=result.path,
                        robot_id=result.hit_robot_id or "",
                        amount=tile.laser_count if result.hit_robot_id else 0,
                    ))

    for robot in alive:
        others = [r for r in alive if r.id != robot.id]
        result = fire_laser(board, others, robot.x, robot.y, robot.facing, 1)
        if result.hit_robot_id:
            events.append(ActivationEvent(
                type="laser", laser_path=result.path,
                robot_id=result.hit_robot_id, amount=1,
            ))

    # --- Sub-step 8: Checkpoints ---
    alive = [r for r in robots if r.is_alive]
    for robot in alive:
        tile = board.tile_at(robot.x, robot.y)
        if tile.type == TileType.CHECKPOINT:
            if tile.checkpoint_num == robot.checkpoints_touched + 1:
                robot.checkpoints_touched += 1
                robot.update_archive(robot.x, robot.y)
                events.append(ActivationEvent(
                    type="checkpoint", robot_id=robot.id,
                    checkpoint_num=tile.checkpoint_num,
                ))
        elif tile.type in (TileType.REPAIR, TileType.DOUBLE_REPAIR):
            robot.update_archive(robot.x, robot.y)

    return events
