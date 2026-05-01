import pytest

from game.board import Board, Direction, TileType
from game.conveyor import apply_conveyors
from game.robot import Robot


def make_robot(id, x, y, facing=Direction.NORTH):
    return Robot(id=id, x=x, y=y, facing=facing)


def place_conveyor(board, x, y, direction, speed=1):
    tile = board.tile_at(x, y)
    tile.type = TileType.CONVEYOR
    tile.direction = direction
    tile.speed = speed


class TestGreenConveyor:
    """Speed-1 conveyors move robots one space per activation step."""

    def setup_method(self):
        self.board = Board.empty(12, 12)

    def test_conveyor_moves_robot_one_step(self):
        place_conveyor(self.board, 5, 5, Direction.NORTH)
        robot = make_robot("r1", x=5, y=5)
        apply_conveyors(self.board, [robot], express_only=False)
        assert robot.y == 4

    def test_conveyor_moves_robot_east(self):
        place_conveyor(self.board, 5, 5, Direction.EAST)
        robot = make_robot("r1", x=5, y=5)
        apply_conveyors(self.board, [robot], express_only=False)
        assert robot.x == 6

    def test_robot_not_on_conveyor_does_not_move(self):
        place_conveyor(self.board, 5, 5, Direction.NORTH)
        robot = make_robot("r1", x=3, y=3)
        apply_conveyors(self.board, [robot], express_only=False)
        assert robot.x == 3
        assert robot.y == 3

    def test_conveyor_blocked_by_wall_does_not_move_robot(self):
        place_conveyor(self.board, 5, 5, Direction.NORTH)
        self.board.tile_at(5, 5).walls.add(Direction.NORTH)
        robot = make_robot("r1", x=5, y=5)
        apply_conveyors(self.board, [robot], express_only=False)
        assert robot.y == 5

    def test_conveyor_off_board_destroys_robot(self):
        place_conveyor(self.board, 5, 0, Direction.NORTH)
        robot = make_robot("r1", x=5, y=0)
        apply_conveyors(self.board, [robot], express_only=False)
        assert not robot.is_alive

    def test_conveyor_into_pit_destroys_robot(self):
        place_conveyor(self.board, 5, 5, Direction.NORTH)
        self.board.tile_at(5, 4).type = TileType.PIT
        robot = make_robot("r1", x=5, y=5)
        apply_conveyors(self.board, [robot], express_only=False)
        assert not robot.is_alive


class TestExpressConveyor:
    """Speed-2 (express/blue) conveyors move robots two spaces per full activation."""

    def setup_method(self):
        self.board = Board.empty(12, 12)

    def test_express_only_step_moves_express_robots(self):
        place_conveyor(self.board, 5, 5, Direction.NORTH, speed=2)
        robot = make_robot("r1", x=5, y=5)
        apply_conveyors(self.board, [robot], express_only=True)
        assert robot.y == 4

    def test_express_only_step_does_not_move_green_robots(self):
        place_conveyor(self.board, 5, 5, Direction.NORTH, speed=1)
        robot = make_robot("r1", x=5, y=5)
        apply_conveyors(self.board, [robot], express_only=True)
        assert robot.y == 5

    def test_full_step_moves_both_express_and_green(self):
        place_conveyor(self.board, 3, 5, Direction.EAST, speed=1)
        place_conveyor(self.board, 7, 5, Direction.WEST, speed=2)
        r_green = make_robot("r1", x=3, y=5)
        r_express = make_robot("r2", x=7, y=5)
        apply_conveyors(self.board, [r_green, r_express], express_only=False)
        assert r_green.x == 4
        assert r_express.x == 6

    def test_two_step_activation_moves_express_two_total(self):
        """Two chained express tiles move a robot 2 spaces across the two sub-steps.
        In sub-step b the robot moves from (5,5) to (5,4) (also express).
        In sub-step c it moves again from (5,4) to (5,3)."""
        place_conveyor(self.board, 5, 5, Direction.NORTH, speed=2)
        place_conveyor(self.board, 5, 4, Direction.NORTH, speed=2)
        robot = make_robot("r1", x=5, y=5)
        apply_conveyors(self.board, [robot], express_only=True)   # step b → (5,4)
        apply_conveyors(self.board, [robot], express_only=False)  # step c → (5,3)
        assert robot.y == 3

    def test_single_express_tile_moves_robot_only_once(self):
        """A lone express tile moves the robot once in step b, then lands on
        a floor tile and does not move again in step c."""
        place_conveyor(self.board, 5, 5, Direction.NORTH, speed=2)
        robot = make_robot("r1", x=5, y=5)
        apply_conveyors(self.board, [robot], express_only=True)   # step b → (5,4)
        apply_conveyors(self.board, [robot], express_only=False)  # step c — floor, no move
        assert robot.y == 4

    def test_two_step_activation_moves_green_one_total(self):
        place_conveyor(self.board, 5, 5, Direction.NORTH, speed=1)
        robot = make_robot("r1", x=5, y=5)
        apply_conveyors(self.board, [robot], express_only=True)   # step b — no move
        apply_conveyors(self.board, [robot], express_only=False)  # step c — moves
        assert robot.y == 4  # moved 1 total


class TestTurningConveyor:
    """A conveyor that turns rotates the robot when it enters from a perpendicular side."""

    def setup_method(self):
        self.board = Board.empty(12, 12)

    def _place_turn(self, x, y, from_dir, to_dir, speed=1):
        """Place a turning conveyor: enters from from_dir, exits to_dir."""
        tile = self.board.tile_at(x, y)
        tile.type = TileType.CONVEYOR
        tile.direction = to_dir       # where the belt pushes the robot to
        tile.speed = speed
        tile.walls = set()
        # Store entry direction so conveyor logic can compute the rotation
        tile._entry_direction = from_dir

    def test_straight_conveyor_does_not_rotate_robot(self):
        place_conveyor(self.board, 5, 6, Direction.NORTH)  # robot enters from south, exits north
        robot = make_robot("r1", x=5, y=6, facing=Direction.EAST)
        apply_conveyors(self.board, [robot], express_only=False)
        assert robot.facing == Direction.EAST  # unchanged

    def test_turning_conveyor_rotates_robot_right(self):
        # Belt goes north but robot enters from west → robot turns right (faces east)
        self._place_turn(5, 5, from_dir=Direction.WEST, to_dir=Direction.NORTH)
        robot = make_robot("r1", x=5, y=5, facing=Direction.EAST)
        apply_conveyors(self.board, [robot], express_only=False)
        assert robot.y == 4           # moved north
        assert robot.facing == Direction.NORTH  # turned to align with exit

    def test_turning_conveyor_rotates_robot_left(self):
        # Belt goes north but robot enters from east → robot turns left (faces west)
        self._place_turn(5, 5, from_dir=Direction.EAST, to_dir=Direction.NORTH)
        robot = make_robot("r1", x=5, y=5, facing=Direction.WEST)
        apply_conveyors(self.board, [robot], express_only=False)
        assert robot.y == 4
        assert robot.facing == Direction.NORTH


class TestMultipleRobotsOnConveyors:
    def setup_method(self):
        self.board = Board.empty(12, 12)

    def test_two_robots_on_same_conveyor_both_move(self):
        place_conveyor(self.board, 5, 5, Direction.NORTH)
        place_conveyor(self.board, 5, 6, Direction.NORTH)
        r1 = make_robot("r1", x=5, y=5)
        r2 = make_robot("r2", x=5, y=6)
        apply_conveyors(self.board, [r1, r2], express_only=False)
        assert r1.y == 4
        assert r2.y == 5

    def test_conveyor_blocked_when_destination_robot_cannot_move(self):
        # r2 is on a conveyor pointing north, but r1 is directly north off a conveyor
        # and there is a wall blocking r1 from moving — r2 should be blocked too
        place_conveyor(self.board, 5, 5, Direction.NORTH)
        self.board.tile_at(5, 4).walls.add(Direction.NORTH)  # wall blocks r1
        r1 = make_robot("r1", x=5, y=4)  # not on conveyor
        r2 = make_robot("r2", x=5, y=5)  # on conveyor, pushing into r1
        apply_conveyors(self.board, [r1, r2], express_only=False)
        assert r2.y == 5   # blocked — cannot push r1 through wall
        assert r1.y == 4
