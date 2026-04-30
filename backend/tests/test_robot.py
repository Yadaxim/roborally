import pytest

from game.board import Board, Direction
from game.robot import Robot, MAX_DAMAGE


class TestRobotCreation:
    def test_robot_has_starting_position(self):
        robot = Robot(id="r1", x=3, y=4, facing=Direction.NORTH)
        assert robot.x == 3
        assert robot.y == 4

    def test_robot_has_facing_direction(self):
        robot = Robot(id="r1", x=0, y=0, facing=Direction.EAST)
        assert robot.facing == Direction.EAST

    def test_robot_starts_with_zero_damage(self):
        robot = Robot(id="r1", x=0, y=0, facing=Direction.NORTH)
        assert robot.damage == 0

    def test_robot_starts_alive(self):
        robot = Robot(id="r1", x=0, y=0, facing=Direction.NORTH)
        assert robot.is_alive

    def test_robot_archive_defaults_to_start_position(self):
        robot = Robot(id="r1", x=3, y=4, facing=Direction.NORTH)
        assert robot.archive == (3, 4)

    def test_robot_starts_with_full_lives(self):
        robot = Robot(id="r1", x=0, y=0, facing=Direction.NORTH)
        assert robot.lives == 3


class TestRobotRotation:
    def setup_method(self):
        self.robot = Robot(id="r1", x=5, y=5, facing=Direction.NORTH)

    def test_rotate_left(self):
        self.robot.rotate_left()
        assert self.robot.facing == Direction.WEST

    def test_rotate_right(self):
        self.robot.rotate_right()
        assert self.robot.facing == Direction.EAST

    def test_rotate_180(self):
        self.robot.rotate_180()
        assert self.robot.facing == Direction.SOUTH

    def test_four_left_rotations_return_to_start(self):
        for _ in range(4):
            self.robot.rotate_left()
        assert self.robot.facing == Direction.NORTH

    def test_rotation_does_not_change_position(self):
        self.robot.rotate_left()
        assert self.robot.x == 5
        assert self.robot.y == 5


class TestRobotMovement:
    def setup_method(self):
        self.board = Board.empty(12, 12)
        self.robot = Robot(id="r1", x=5, y=5, facing=Direction.NORTH)

    def test_move_forward_one_step(self):
        self.robot.move_forward(self.board, steps=1)
        assert self.robot.x == 5
        assert self.robot.y == 4

    def test_move_forward_two_steps(self):
        self.robot.move_forward(self.board, steps=2)
        assert self.robot.y == 3

    def test_move_forward_three_steps(self):
        self.robot.move_forward(self.board, steps=3)
        assert self.robot.y == 2

    def test_move_backward(self):
        self.robot.move_backward(self.board)
        assert self.robot.y == 6

    def test_move_respects_facing_direction_east(self):
        self.robot.facing = Direction.EAST
        self.robot.move_forward(self.board, steps=1)
        assert self.robot.x == 6
        assert self.robot.y == 5

    def test_move_stops_at_wall(self):
        self.board.tile_at(5, 5).walls.add(Direction.NORTH)
        self.robot.move_forward(self.board, steps=3)
        assert self.robot.y == 5  # blocked immediately, no movement

    def test_move_stops_mid_path_at_wall(self):
        # Wall after 1 step: robot should stop at (5,4)
        self.board.tile_at(5, 4).walls.add(Direction.NORTH)
        self.robot.move_forward(self.board, steps=3)
        assert self.robot.y == 4

    def test_move_off_board_destroys_robot(self):
        self.robot = Robot(id="r1", x=5, y=0, facing=Direction.NORTH)
        self.robot.move_forward(self.board, steps=1)
        assert not self.robot.is_alive

    def test_move_does_not_change_facing(self):
        self.robot.move_forward(self.board, steps=2)
        assert self.robot.facing == Direction.NORTH


class TestRobotDamage:
    def setup_method(self):
        self.robot = Robot(id="r1", x=5, y=5, facing=Direction.NORTH)

    def test_take_damage_increments_counter(self):
        self.robot.take_damage(1)
        assert self.robot.damage == 1

    def test_take_multiple_damage(self):
        self.robot.take_damage(3)
        assert self.robot.damage == 3

    def test_max_damage_destroys_robot(self):
        self.robot.take_damage(MAX_DAMAGE)
        assert not self.robot.is_alive

    def test_damage_below_max_keeps_robot_alive(self):
        self.robot.take_damage(MAX_DAMAGE - 1)
        assert self.robot.is_alive

    def test_hand_size_reduced_by_damage(self):
        self.robot.take_damage(3)
        assert self.robot.hand_size == 9 - 3

    def test_hand_size_at_zero_damage(self):
        assert self.robot.hand_size == 9

    def test_hand_size_minimum_is_zero(self):
        self.robot.take_damage(MAX_DAMAGE)
        assert self.robot.hand_size == 0

    def test_locked_registers_count_at_high_damage(self):
        # Registers lock from 5 backward when damage >= 5
        self.robot.take_damage(5)
        assert self.robot.locked_registers == {5}

    def test_locked_registers_at_max_damage(self):
        self.robot.take_damage(9)
        assert self.robot.locked_registers == {5, 4, 3, 2, 1}

    def test_no_locked_registers_at_low_damage(self):
        self.robot.take_damage(4)
        assert self.robot.locked_registers == set()


class TestRobotArchive:
    def test_archive_updates_on_checkpoint(self):
        robot = Robot(id="r1", x=0, y=0, facing=Direction.NORTH)
        robot.update_archive(5, 5)
        assert robot.archive == (5, 5)

    def test_respawn_restores_position_from_archive(self):
        robot = Robot(id="r1", x=0, y=0, facing=Direction.NORTH)
        robot.update_archive(7, 3)
        robot.take_damage(MAX_DAMAGE)
        robot.respawn()
        assert robot.x == 7
        assert robot.y == 3

    def test_respawn_restores_life_with_two_damage(self):
        robot = Robot(id="r1", x=0, y=0, facing=Direction.NORTH)
        robot.take_damage(MAX_DAMAGE)
        robot.respawn()
        assert robot.is_alive
        assert robot.damage == 2

    def test_respawn_costs_one_life(self):
        robot = Robot(id="r1", x=0, y=0, facing=Direction.NORTH)
        lives_before = robot.lives
        robot.take_damage(MAX_DAMAGE)
        robot.respawn()
        assert robot.lives == lives_before - 1

    def test_robot_eliminated_when_lives_exhausted(self):
        robot = Robot(id="r1", x=0, y=0, facing=Direction.NORTH)
        for _ in range(robot.lives):
            robot.take_damage(MAX_DAMAGE)
            robot.respawn()
        assert not robot.is_alive
        assert robot.lives == 0
