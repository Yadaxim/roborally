import pytest

from game.board import Board, Direction, TileType
from game.laser import LaserResult, fire_laser
from game.robot import Robot


def make_robot(id, x, y, facing=Direction.NORTH):
    return Robot(id=id, x=x, y=y, facing=facing)


class TestLaserPath:
    def setup_method(self):
        self.board = Board.empty(12, 12)

    def test_laser_returns_cells_it_traversed(self):
        robots = []
        result = fire_laser(self.board, robots, x=0, y=5, direction=Direction.EAST, count=1)
        assert len(result.path) > 0

    def test_laser_travels_full_row_with_no_obstacles(self):
        result = fire_laser(self.board, [], x=0, y=5, direction=Direction.EAST, count=1)
        assert result.path == [(x, 5) for x in range(1, 12)]

    def test_laser_travels_full_column_northward(self):
        result = fire_laser(self.board, [], x=5, y=11, direction=Direction.NORTH, count=1)
        assert result.path == [(5, y) for y in range(10, -1, -1)]

    def test_laser_stops_at_board_edge(self):
        result = fire_laser(self.board, [], x=0, y=5, direction=Direction.WEST, count=1)
        assert result.path == []

    def test_laser_does_not_include_start_cell(self):
        result = fire_laser(self.board, [], x=5, y=5, direction=Direction.EAST, count=1)
        assert (5, 5) not in result.path

    def test_laser_stops_at_wall_on_source_tile(self):
        self.board.tile_at(5, 5).walls.add(Direction.EAST)
        result = fire_laser(self.board, [], x=5, y=5, direction=Direction.EAST, count=1)
        assert result.path == []

    def test_laser_stops_at_wall_on_destination_tile(self):
        # Wall on west face of (7,5) blocks a laser coming from the west
        self.board.tile_at(7, 5).walls.add(Direction.WEST)
        result = fire_laser(self.board, [], x=5, y=5, direction=Direction.EAST, count=1)
        assert result.path == [(6, 5)]

    def test_laser_path_is_empty_when_immediately_wall_blocked(self):
        self.board.tile_at(5, 5).walls.add(Direction.NORTH)
        result = fire_laser(self.board, [], x=5, y=5, direction=Direction.NORTH, count=1)
        assert result.path == []


class TestLaserHits:
    def setup_method(self):
        self.board = Board.empty(12, 12)

    def test_laser_hits_first_robot_in_path(self):
        robot = make_robot("r1", x=5, y=5)
        result = fire_laser(self.board, [robot], x=0, y=5, direction=Direction.EAST, count=1)
        assert result.hit_robot_id == "r1"

    def test_laser_deals_one_damage_by_default(self):
        robot = make_robot("r1", x=5, y=5)
        fire_laser(self.board, [robot], x=0, y=5, direction=Direction.EAST, count=1)
        assert robot.damage == 1

    def test_double_laser_deals_two_damage(self):
        robot = make_robot("r1", x=5, y=5)
        fire_laser(self.board, [robot], x=0, y=5, direction=Direction.EAST, count=2)
        assert robot.damage == 2

    def test_laser_stops_at_first_robot_does_not_hit_second(self):
        r1 = make_robot("r1", x=5, y=5)
        r2 = make_robot("r2", x=8, y=5)
        result = fire_laser(self.board, [r1, r2], x=0, y=5, direction=Direction.EAST, count=1)
        assert result.hit_robot_id == "r1"
        assert r1.damage == 1
        assert r2.damage == 0

    def test_laser_path_stops_at_hit_robot(self):
        robot = make_robot("r1", x=5, y=5)
        result = fire_laser(self.board, [robot], x=0, y=5, direction=Direction.EAST, count=1)
        assert result.path[-1] == (5, 5)
        assert (6, 5) not in result.path

    def test_laser_with_no_robot_in_path_has_no_hit(self):
        result = fire_laser(self.board, [], x=0, y=5, direction=Direction.EAST, count=1)
        assert result.hit_robot_id is None

    def test_robot_behind_wall_not_hit(self):
        self.board.tile_at(7, 5).walls.add(Direction.WEST)
        robot = make_robot("r1", x=8, y=5)
        result = fire_laser(self.board, [robot], x=0, y=5, direction=Direction.EAST, count=1)
        assert result.hit_robot_id is None
        assert robot.damage == 0

    def test_robot_at_wall_boundary_on_correct_side_is_hit(self):
        # Wall on east face of (6,5) — laser coming from west still reaches (6,5)
        self.board.tile_at(6, 5).walls.add(Direction.EAST)
        robot = make_robot("r1", x=6, y=5)
        result = fire_laser(self.board, [robot], x=0, y=5, direction=Direction.EAST, count=1)
        assert result.hit_robot_id == "r1"
        assert robot.damage == 1

    def test_laser_does_not_hit_robot_at_start_position(self):
        # Laser fires from same cell as robot — robot is the emitter, not a target
        robot = make_robot("r1", x=0, y=5)
        result = fire_laser(self.board, [robot], x=0, y=5, direction=Direction.EAST, count=1)
        assert result.hit_robot_id is None


class TestRobotLaser:
    """Robot-mounted lasers fire from the robot's position in its facing direction."""

    def setup_method(self):
        self.board = Board.empty(12, 12)

    def test_robot_laser_fires_in_facing_direction(self):
        shooter = make_robot("shooter", x=0, y=5, facing=Direction.EAST)
        target = make_robot("target", x=5, y=5)
        result = fire_laser(
            self.board, [shooter, target],
            x=shooter.x, y=shooter.y, direction=shooter.facing, count=1
        )
        assert result.hit_robot_id == "target"

    def test_robot_does_not_shoot_itself(self):
        shooter = make_robot("shooter", x=0, y=5, facing=Direction.EAST)
        result = fire_laser(
            self.board, [shooter],
            x=shooter.x, y=shooter.y, direction=shooter.facing, count=1
        )
        assert shooter.damage == 0
