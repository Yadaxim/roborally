import pytest

from game.activation import ActivationEvent, execute_register
from game.board import Board, Direction, TileType
from game.cards import Card, CardType
from game.robot import Robot


def make_robot(id, x, y, facing=Direction.NORTH):
    return Robot(id=id, x=x, y=y, facing=facing)


def card(type, priority=500):
    return Card(type=type, priority=priority)


def assignments(*pairs):
    """Build {robot_id: card} from alternating (robot, card) pairs."""
    return {r.id: c for r, c in pairs}


class TestSubStep1Cards:
    """Robots execute their card in priority order."""

    def setup_method(self):
        self.board = Board.empty(12, 12)

    def test_move1_moves_robot_forward(self):
        robot = make_robot("r1", x=5, y=5, facing=Direction.NORTH)
        execute_register(self.board, [robot], assignments((robot, card(CardType.MOVE_1))), 1)
        assert robot.y == 4

    def test_move2_moves_robot_two_steps(self):
        robot = make_robot("r1", x=5, y=5, facing=Direction.NORTH)
        execute_register(self.board, [robot], assignments((robot, card(CardType.MOVE_2))), 1)
        assert robot.y == 3

    def test_move3_moves_robot_three_steps(self):
        robot = make_robot("r1", x=5, y=5, facing=Direction.NORTH)
        execute_register(self.board, [robot], assignments((robot, card(CardType.MOVE_3))), 1)
        assert robot.y == 2

    def test_backup_moves_robot_backward(self):
        robot = make_robot("r1", x=5, y=5, facing=Direction.NORTH)
        execute_register(self.board, [robot], assignments((robot, card(CardType.BACK_UP))), 1)
        assert robot.y == 6

    def test_turn_left_rotates_robot(self):
        robot = make_robot("r1", x=5, y=5, facing=Direction.NORTH)
        execute_register(self.board, [robot], assignments((robot, card(CardType.TURN_LEFT))), 1)
        assert robot.facing == Direction.WEST
        assert robot.x == 5 and robot.y == 5

    def test_turn_right_rotates_robot(self):
        robot = make_robot("r1", x=5, y=5, facing=Direction.NORTH)
        execute_register(self.board, [robot], assignments((robot, card(CardType.TURN_RIGHT))), 1)
        assert robot.facing == Direction.EAST

    def test_uturn_reverses_facing(self):
        robot = make_robot("r1", x=5, y=5, facing=Direction.NORTH)
        execute_register(self.board, [robot], assignments((robot, card(CardType.U_TURN))), 1)
        assert robot.facing == Direction.SOUTH

    def test_higher_priority_executes_first(self):
        # r1 (priority 600) moves north first, blocking r2's path
        r1 = make_robot("r1", x=5, y=4, facing=Direction.NORTH)
        r2 = make_robot("r2", x=5, y=5, facing=Direction.NORTH)
        result = execute_register(
            self.board, [r1, r2],
            {r1.id: card(CardType.MOVE_1, priority=600),
             r2.id: card(CardType.MOVE_1, priority=400)},
            1
        )
        # r1 moves to (5,3); r2 then moves to (5,4), pushing nobody
        assert r1.y == 3
        assert r2.y == 4

    def test_moving_robot_pushes_robot_in_the_way(self):
        r1 = make_robot("r1", x=5, y=5, facing=Direction.NORTH)
        r2 = make_robot("r2", x=5, y=4)  # directly in r1's path
        execute_register(
            self.board, [r1, r2],
            {r1.id: card(CardType.MOVE_1), r2.id: card(CardType.U_TURN, priority=100)},
            1
        )
        assert r1.y == 4
        assert r2.y == 3  # pushed

    def test_robot_with_no_card_does_not_move(self):
        r1 = make_robot("r1", x=5, y=5, facing=Direction.NORTH)
        r2 = make_robot("r2", x=3, y=3, facing=Direction.EAST)
        execute_register(self.board, [r1, r2], {r1.id: card(CardType.MOVE_1)}, 1)
        assert r2.x == 3 and r2.y == 3


class TestSubStep2And3Conveyors:
    def setup_method(self):
        self.board = Board.empty(12, 12)

    def test_conveyor_moves_robot_after_card_execution(self):
        self.board.tile_at(5, 4).type = TileType.CONVEYOR
        self.board.tile_at(5, 4).direction = Direction.NORTH
        self.board.tile_at(5, 4).speed = 1
        robot = make_robot("r1", x=5, y=5, facing=Direction.NORTH)
        execute_register(self.board, [robot], assignments((robot, card(CardType.MOVE_1))), 1)
        # Card moves to (5,4), conveyor moves to (5,3)
        assert robot.y == 3

    def test_express_conveyor_moves_robot_twice_when_chained(self):
        for y in [4, 3]:
            self.board.tile_at(5, y).type = TileType.CONVEYOR
            self.board.tile_at(5, y).direction = Direction.NORTH
            self.board.tile_at(5, y).speed = 2
        robot = make_robot("r1", x=5, y=5, facing=Direction.NORTH)
        execute_register(self.board, [robot], assignments((robot, card(CardType.MOVE_1))), 1)
        # Card→(5,4), sub-step b express→(5,3), sub-step c express→(5,2)
        assert robot.y == 2


class TestSubStep5Gears:
    def setup_method(self):
        self.board = Board.empty(12, 12)

    def test_clockwise_gear_rotates_robot_right(self):
        self.board.tile_at(5, 4).type = TileType.GEAR
        self.board.tile_at(5, 4).rotation = "clockwise"
        robot = make_robot("r1", x=5, y=5, facing=Direction.NORTH)
        execute_register(self.board, [robot], assignments((robot, card(CardType.MOVE_1))), 1)
        assert robot.y == 4
        assert robot.facing == Direction.EAST

    def test_counter_clockwise_gear_rotates_robot_left(self):
        self.board.tile_at(5, 4).type = TileType.GEAR
        self.board.tile_at(5, 4).rotation = "counter_clockwise"
        robot = make_robot("r1", x=5, y=5, facing=Direction.NORTH)
        execute_register(self.board, [robot], assignments((robot, card(CardType.MOVE_1))), 1)
        assert robot.facing == Direction.WEST

    def test_gear_on_starting_tile_also_rotates(self):
        self.board.tile_at(5, 5).type = TileType.GEAR
        self.board.tile_at(5, 5).rotation = "clockwise"
        robot = make_robot("r1", x=5, y=5, facing=Direction.NORTH)
        execute_register(self.board, [robot], assignments((robot, card(CardType.U_TURN))), 1)
        # U-turn makes it face south; gear then rotates right → west
        assert robot.facing == Direction.WEST


class TestSubStep7Lasers:
    def setup_method(self):
        self.board = Board.empty(12, 12)

    def test_board_laser_damages_robot_in_path(self):
        self.board.tile_at(0, 5).type = TileType.LASER_EMITTER
        self.board.tile_at(0, 5).direction = Direction.EAST
        self.board.tile_at(0, 5).laser_count = 1
        robot = make_robot("r1", x=5, y=5)
        execute_register(self.board, [robot], assignments((robot, card(CardType.U_TURN))), 1)
        assert robot.damage == 1

    def test_robots_shoot_each_other(self):
        # Facing each other with no cards — robots keep facing and fire in laser step
        r1 = make_robot("r1", x=3, y=5, facing=Direction.EAST)
        r2 = make_robot("r2", x=7, y=5, facing=Direction.WEST)
        execute_register(self.board, [r1, r2], {}, 1)
        assert r1.damage == 1
        assert r2.damage == 1


class TestSubStep8Checkpoints:
    def setup_method(self):
        self.board = Board.empty(12, 12)
        self.board.checkpoints = [(5, 4), (8, 8)]
        self.board.tile_at(5, 4).type = TileType.CHECKPOINT
        self.board.tile_at(5, 4).checkpoint_num = 1
        self.board.tile_at(8, 8).type = TileType.CHECKPOINT
        self.board.tile_at(8, 8).checkpoint_num = 2

    def test_robot_touching_first_checkpoint_records_it(self):
        robot = make_robot("r1", x=5, y=5, facing=Direction.NORTH)
        robot.checkpoints_touched = 0
        execute_register(self.board, [robot], assignments((robot, card(CardType.MOVE_1))), 1)
        assert robot.checkpoints_touched == 1

    def test_robot_cannot_skip_to_second_checkpoint(self):
        robot = make_robot("r1", x=8, y=9, facing=Direction.NORTH)
        robot.checkpoints_touched = 0  # hasn't touched checkpoint 1 yet
        execute_register(self.board, [robot], assignments((robot, card(CardType.MOVE_1))), 1)
        assert robot.checkpoints_touched == 0

    def test_robot_touches_second_checkpoint_after_first(self):
        robot = make_robot("r1", x=8, y=9, facing=Direction.NORTH)
        robot.checkpoints_touched = 1  # already touched checkpoint 1
        execute_register(self.board, [robot], assignments((robot, card(CardType.MOVE_1))), 1)
        assert robot.checkpoints_touched == 2

    def test_checkpoint_updates_archive(self):
        robot = make_robot("r1", x=5, y=5, facing=Direction.NORTH)
        robot.checkpoints_touched = 0
        execute_register(self.board, [robot], assignments((robot, card(CardType.MOVE_1))), 1)
        assert robot.archive == (5, 4)


class TestActivationEvents:
    def setup_method(self):
        self.board = Board.empty(12, 12)

    def test_returns_list_of_events(self):
        robot = make_robot("r1", x=5, y=5, facing=Direction.NORTH)
        events = execute_register(self.board, [robot], assignments((robot, card(CardType.MOVE_1))), 1)
        assert isinstance(events, list)

    def test_move_event_emitted(self):
        robot = make_robot("r1", x=5, y=5, facing=Direction.NORTH)
        events = execute_register(self.board, [robot], assignments((robot, card(CardType.MOVE_1))), 1)
        move_events = [e for e in events if e.type == "move"]
        assert len(move_events) == 1
        assert move_events[0].robot_id == "r1"
        assert move_events[0].to == (5, 4)

    def test_rotate_event_emitted(self):
        robot = make_robot("r1", x=5, y=5, facing=Direction.NORTH)
        events = execute_register(self.board, [robot], assignments((robot, card(CardType.TURN_LEFT))), 1)
        rotate_events = [e for e in events if e.type == "rotate"]
        assert len(rotate_events) == 1
        assert rotate_events[0].robot_id == "r1"

    def test_checkpoint_event_emitted(self):
        self.board.checkpoints = [(5, 4)]
        self.board.tile_at(5, 4).type = TileType.CHECKPOINT
        self.board.tile_at(5, 4).checkpoint_num = 1
        robot = make_robot("r1", x=5, y=5, facing=Direction.NORTH)
        robot.checkpoints_touched = 0
        events = execute_register(self.board, [robot], assignments((robot, card(CardType.MOVE_1))), 1)
        cp_events = [e for e in events if e.type == "checkpoint"]
        assert len(cp_events) == 1
        assert cp_events[0].robot_id == "r1"
