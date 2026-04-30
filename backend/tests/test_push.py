import pytest

from game.board import Board, Direction
from game.push import push_robots
from game.robot import Robot


def make_robot(id, x, y, facing=Direction.NORTH):
    return Robot(id=id, x=x, y=y, facing=facing)


def robots_by_id(robots):
    return {r.id: r for r in robots}


class TestSinglePush:
    def setup_method(self):
        self.board = Board.empty(12, 12)

    def test_push_moves_robot_one_step(self):
        robot = make_robot("r1", x=5, y=5)
        push_robots(self.board, [robot], pusher_x=5, pusher_y=6, direction=Direction.NORTH)
        assert robot.y == 4

    def test_push_east_moves_robot_east(self):
        robot = make_robot("r1", x=5, y=5)
        push_robots(self.board, [robot], pusher_x=4, pusher_y=5, direction=Direction.EAST)
        assert robot.x == 6
        assert robot.y == 5

    def test_push_does_not_move_robot_not_in_path(self):
        robot = make_robot("r1", x=3, y=3)
        push_robots(self.board, [robot], pusher_x=5, pusher_y=6, direction=Direction.NORTH)
        assert robot.x == 3
        assert robot.y == 3

    def test_push_blocked_by_wall_on_source_tile(self):
        robot = make_robot("r1", x=5, y=5)
        self.board.tile_at(5, 5).walls.add(Direction.NORTH)
        push_robots(self.board, [robot], pusher_x=5, pusher_y=6, direction=Direction.NORTH)
        assert robot.y == 5  # not moved

    def test_push_blocked_by_wall_on_destination_tile(self):
        robot = make_robot("r1", x=5, y=5)
        self.board.tile_at(5, 4).walls.add(Direction.SOUTH)
        push_robots(self.board, [robot], pusher_x=5, pusher_y=6, direction=Direction.NORTH)
        assert robot.y == 5  # not moved

    def test_push_off_board_destroys_robot(self):
        robot = make_robot("r1", x=5, y=0)
        push_robots(self.board, [robot], pusher_x=5, pusher_y=1, direction=Direction.NORTH)
        assert not robot.is_alive

    def test_push_into_pit_destroys_robot(self):
        from game.board import TileType
        self.board.tile_at(5, 4).type = TileType.PIT
        robot = make_robot("r1", x=5, y=5)
        push_robots(self.board, [robot], pusher_x=5, pusher_y=6, direction=Direction.NORTH)
        assert not robot.is_alive


class TestChainPush:
    def setup_method(self):
        self.board = Board.empty(12, 12)

    def test_chain_push_two_robots(self):
        r1 = make_robot("r1", x=5, y=5)
        r2 = make_robot("r2", x=5, y=4)  # directly north of r1
        push_robots(self.board, [r1, r2], pusher_x=5, pusher_y=6, direction=Direction.NORTH)
        assert r1.y == 4
        assert r2.y == 3

    def test_chain_push_three_robots(self):
        r1 = make_robot("r1", x=5, y=5)
        r2 = make_robot("r2", x=5, y=4)
        r3 = make_robot("r3", x=5, y=3)
        push_robots(self.board, [r1, r2, r3], pusher_x=5, pusher_y=6, direction=Direction.NORTH)
        assert r1.y == 4
        assert r2.y == 3
        assert r3.y == 2

    def test_chain_blocked_by_wall_stops_entire_chain(self):
        r1 = make_robot("r1", x=5, y=5)
        r2 = make_robot("r2", x=5, y=4)
        self.board.tile_at(5, 4).walls.add(Direction.NORTH)  # wall blocks r2
        push_robots(self.board, [r1, r2], pusher_x=5, pusher_y=6, direction=Direction.NORTH)
        assert r1.y == 5  # chain is stuck, r1 not moved either
        assert r2.y == 4

    def test_chain_off_board_destroys_last_robot(self):
        r1 = make_robot("r1", x=5, y=1)
        r2 = make_robot("r2", x=5, y=0)  # r2 at board edge
        push_robots(self.board, [r1, r2], pusher_x=5, pusher_y=2, direction=Direction.NORTH)
        assert r1.y == 0
        assert not r2.is_alive

    def test_non_adjacent_robot_not_included_in_chain(self):
        r1 = make_robot("r1", x=5, y=5)
        r2 = make_robot("r2", x=5, y=3)  # gap between r1 and r2
        push_robots(self.board, [r1, r2], pusher_x=5, pusher_y=6, direction=Direction.NORTH)
        assert r1.y == 4
        assert r2.y == 3  # not pushed (not adjacent to r1)

    def test_robots_on_different_column_not_pushed(self):
        r1 = make_robot("r1", x=5, y=5)
        r2 = make_robot("r2", x=6, y=5)  # same row, different column
        push_robots(self.board, [r1, r2], pusher_x=5, pusher_y=6, direction=Direction.NORTH)
        assert r1.y == 4
        assert r2.x == 6
        assert r2.y == 5  # not in push path


class TestPushReturnValue:
    def setup_method(self):
        self.board = Board.empty(12, 12)

    def test_returns_list_of_moved_robot_ids(self):
        r1 = make_robot("r1", x=5, y=5)
        moved = push_robots(self.board, [r1], pusher_x=5, pusher_y=6, direction=Direction.NORTH)
        assert "r1" in moved

    def test_returns_empty_when_push_blocked(self):
        r1 = make_robot("r1", x=5, y=5)
        self.board.tile_at(5, 5).walls.add(Direction.NORTH)
        moved = push_robots(self.board, [r1], pusher_x=5, pusher_y=6, direction=Direction.NORTH)
        assert moved == []

    def test_returns_all_chain_members_when_moved(self):
        r1 = make_robot("r1", x=5, y=5)
        r2 = make_robot("r2", x=5, y=4)
        moved = push_robots(self.board, [r1, r2], pusher_x=5, pusher_y=6, direction=Direction.NORTH)
        assert "r1" in moved
        assert "r2" in moved
