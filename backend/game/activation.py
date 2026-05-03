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


# Keys for WS / HUD (rules order within one register).
REGISTER_SUBSTEPS: tuple[str, ...] = (
    "program_cards",
    "conveyors_express",
    "conveyors_normal",
    "pushers",
    "gears",
    "crushers",
    "lasers",
    "checkpoints",
)


def _step_robot(
    board: Board,
    robot: Robot,
    direction: Direction,
    all_robots: list[Robot],
    events: list[ActivationEvent],
) -> None:
    """Move robot one step in direction, pushing any occupant. Emits events."""
    from_pos = (robot.x, robot.y)

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


def _snapshot_xy(robots: list[Robot]) -> dict[str, tuple[int, int]]:
    return {r.id: (r.x, r.y) for r in robots if r.is_alive}


def _emit_motion_since_snapshot(
    before_xy: dict[str, tuple[int, int]],
    robots: list[Robot],
    events: list[ActivationEvent],
) -> None:
    for r in robots:
        if r.id not in before_xy:
            continue
        prev = before_xy[r.id]
        if not r.is_alive:
            events.append(ActivationEvent(type="destroy", robot_id=r.id, from_pos=prev))
        elif (r.x, r.y) != prev:
            events.append(ActivationEvent(type="move", robot_id=r.id, from_pos=prev, to=(r.x, r.y)))


def flatten_register_batches(
    batches: list[tuple[str, list[ActivationEvent]]],
) -> list[ActivationEvent]:
    return [ev for _, lst in batches for ev in lst]


def run_register_substep(
    board: Board,
    robots: list[Robot],
    card_assignments: dict[str, Card],
    register_num: int,
    substep: int,
) -> tuple[str, list[ActivationEvent]]:
    """Execute exactly one rules sub-step (1–8) for the current register."""
    if substep < 1 or substep > len(REGISTER_SUBSTEPS):
        raise ValueError(f"substep must be 1–{len(REGISTER_SUBSTEPS)}")
    key = REGISTER_SUBSTEPS[substep - 1]

    if substep == 1:
        events: list[ActivationEvent] = []
        alive = [r for r in robots if r.is_alive]
        ordered = sorted(
            [(r, card_assignments[r.id]) for r in alive if r.id in card_assignments],
            key=lambda x: x[1].priority,
            reverse=True,
        )
        for robot, card in ordered:
            if robot.is_alive:
                _apply_card(board, robot, card, robots, events)
        return (key, events)

    if substep == 2:
        events: list[ActivationEvent] = []
        alive = [r for r in robots if r.is_alive]
        apply_conveyors(board, alive, express_only=True, events=events)
        return (key, events)

    if substep == 3:
        events: list[ActivationEvent] = []
        alive = [r for r in robots if r.is_alive]
        apply_conveyors(board, alive, express_only=False, events=events)
        return (key, events)

    if substep == 4:
        events: list[ActivationEvent] = []
        alive = [r for r in robots if r.is_alive]
        before_xy = _snapshot_xy(alive)
        for y in range(board.height):
            for x in range(board.width):
                tile = board.tile_at(x, y)
                if tile.type == TileType.PUSHER and register_num in tile.active_registers:
                    push_robots(board, alive, x, y, tile.direction)
        _emit_motion_since_snapshot(before_xy, robots, events)
        return (key, events)

    if substep == 5:
        events: list[ActivationEvent] = []
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
        return (key, events)

    if substep == 6:
        events: list[ActivationEvent] = []
        alive = [r for r in robots if r.is_alive]
        for y in range(board.height):
            for x in range(board.width):
                tile = board.tile_at(x, y)
                if tile.type == TileType.CRUSHER and register_num in tile.active_registers:
                    for robot in alive:
                        if robot.x == x and robot.y == y:
                            robot._destroy()
                            events.append(ActivationEvent(type="destroy", robot_id=robot.id))
        return (key, events)

    if substep == 7:
        events: list[ActivationEvent] = []
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
        return (key, events)

    # substep == 8
    events: list[ActivationEvent] = []
    alive = [r for r in robots if r.is_alive]
    for robot in alive:
        tile = board.tile_at(robot.x, robot.y)
        if tile.type == TileType.CHECKPOINT:
            if tile.checkpoint_num == robot.checkpoints_touched + 1:
                robot.checkpoints_touched += 1
                robot.update_archive(robot.x, robot.y)
                robot.damage = max(0, robot.damage - 1)
                events.append(ActivationEvent(
                    type="checkpoint", robot_id=robot.id,
                    checkpoint_num=tile.checkpoint_num,
                ))
        elif tile.type == TileType.REPAIR:
            robot.update_archive(robot.x, robot.y)
            robot.damage = max(0, robot.damage - 1)
        elif tile.type == TileType.DOUBLE_REPAIR:
            robot.update_archive(robot.x, robot.y)
            robot.damage = max(0, robot.damage - 2)

    return (key, events)


def execute_register_flat(
    board: Board,
    robots: list[Robot],
    card_assignments: dict[str, Card],
    register_num: int,
) -> list[ActivationEvent]:
    """Run all 8 sub-steps and concatenate events (tests)."""
    out: list[ActivationEvent] = []
    for s in range(1, len(REGISTER_SUBSTEPS) + 1):
        _, evs = run_register_substep(board, robots, card_assignments, register_num, s)
        out.extend(evs)
    return out
