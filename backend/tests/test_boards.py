"""Tests for board JSON data files."""
import json
import pathlib

import pytest

from game.board import Board, TileType, Direction


BOARDS_DIR = pathlib.Path(__file__).parent.parent / "data" / "boards"


def load_board(name: str) -> Board:
    path = BOARDS_DIR / f"{name}.json"
    return Board.from_dict(json.loads(path.read_text()))


class TestDizzyHighway:
    @pytest.fixture(autouse=True)
    def board(self):
        self.board = load_board("dizzy_highway")

    def test_dimensions(self):
        assert self.board.width == 12
        assert self.board.height == 12

    def test_four_start_positions(self):
        assert len(self.board.start_positions) == 4

    def test_three_checkpoints(self):
        assert len(self.board.checkpoints) == 3

    def test_checkpoints_numbered_sequentially(self):
        nums = sorted(
            self.board.tile_at(x, y).checkpoint_num
            for x, y in self.board.checkpoints
        )
        assert nums == [1, 2, 3]

    def test_has_conveyor_tiles(self):
        conveyors = [
            (x, y)
            for y in range(self.board.height)
            for x in range(self.board.width)
            if self.board.tile_at(x, y).type == TileType.CONVEYOR
        ]
        assert len(conveyors) >= 4

    def test_has_gear_tiles(self):
        gears = [
            (x, y)
            for y in range(self.board.height)
            for x in range(self.board.width)
            if self.board.tile_at(x, y).type == TileType.GEAR
        ]
        assert len(gears) >= 2

    def test_has_pit_tiles(self):
        pits = [
            (x, y)
            for y in range(self.board.height)
            for x in range(self.board.width)
            if self.board.tile_at(x, y).type == TileType.PIT
        ]
        assert len(pits) >= 2

    def test_has_laser_emitter(self):
        emitters = [
            (x, y)
            for y in range(self.board.height)
            for x in range(self.board.width)
            if self.board.tile_at(x, y).type == TileType.LASER_EMITTER
        ]
        assert len(emitters) >= 1

    def test_start_positions_are_on_board(self):
        for x, y in self.board.start_positions:
            assert self.board.in_bounds(x, y)

    def test_checkpoints_are_on_board(self):
        for x, y in self.board.checkpoints:
            assert self.board.in_bounds(x, y)

    def test_express_conveyors_have_speed_two(self):
        express = [
            (x, y)
            for y in range(self.board.height)
            for x in range(self.board.width)
            if self.board.tile_at(x, y).type == TileType.CONVEYOR
            and self.board.tile_at(x, y).speed == 2
        ]
        assert len(express) >= 3
