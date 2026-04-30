import pytest

from game.board import Board, Direction, Tile, TileType, opposite, turn_left, turn_right


class TestDirection:
    def test_turn_left_from_north_gives_west(self):
        assert turn_left(Direction.NORTH) == Direction.WEST

    def test_turn_left_from_west_gives_south(self):
        assert turn_left(Direction.WEST) == Direction.SOUTH

    def test_turn_left_from_south_gives_east(self):
        assert turn_left(Direction.SOUTH) == Direction.EAST

    def test_turn_left_from_east_gives_north(self):
        assert turn_left(Direction.EAST) == Direction.NORTH

    def test_turn_right_from_north_gives_east(self):
        assert turn_right(Direction.NORTH) == Direction.EAST

    def test_turn_right_is_inverse_of_turn_left(self):
        for d in Direction:
            assert turn_right(turn_left(d)) == d

    def test_opposite_north_is_south(self):
        assert opposite(Direction.NORTH) == Direction.SOUTH

    def test_opposite_east_is_west(self):
        assert opposite(Direction.EAST) == Direction.WEST

    def test_opposite_is_symmetric(self):
        for d in Direction:
            assert opposite(opposite(d)) == d

    def test_two_lefts_equal_opposite(self):
        for d in Direction:
            assert turn_left(turn_left(d)) == opposite(d)

    def test_four_lefts_return_to_start(self):
        for d in Direction:
            result = d
            for _ in range(4):
                result = turn_left(result)
            assert result == d


class TestTile:
    def test_default_tile_is_floor(self):
        assert Tile().type == TileType.FLOOR

    def test_default_tile_has_no_walls(self):
        assert Tile().walls == set()

    def test_tiles_with_same_data_are_equal(self):
        assert Tile() == Tile()

    def test_tiles_are_independent(self):
        a, b = Tile(), Tile()
        a.walls.add(Direction.NORTH)
        assert Direction.NORTH not in b.walls


class TestBoardCreation:
    def test_empty_board_has_correct_dimensions(self):
        board = Board.empty(12, 12)
        assert board.width == 12
        assert board.height == 12

    def test_empty_board_all_tiles_are_floor(self):
        board = Board.empty(4, 4)
        for y in range(4):
            for x in range(4):
                assert board.tile_at(x, y).type == TileType.FLOOR

    def test_empty_board_no_walls_anywhere(self):
        board = Board.empty(4, 4)
        for y in range(4):
            for x in range(4):
                assert board.tile_at(x, y).walls == set()

    def test_tiles_are_independent_between_cells(self):
        board = Board.empty(4, 4)
        board.tile_at(0, 0).walls.add(Direction.NORTH)
        assert Direction.NORTH not in board.tile_at(1, 0).walls


class TestBoardBounds:
    def setup_method(self):
        self.board = Board.empty(12, 12)

    def test_corners_are_in_bounds(self):
        assert self.board.in_bounds(0, 0)
        assert self.board.in_bounds(11, 0)
        assert self.board.in_bounds(0, 11)
        assert self.board.in_bounds(11, 11)

    def test_outside_east_is_out_of_bounds(self):
        assert not self.board.in_bounds(12, 0)

    def test_outside_south_is_out_of_bounds(self):
        assert not self.board.in_bounds(0, 12)

    def test_negative_x_is_out_of_bounds(self):
        assert not self.board.in_bounds(-1, 0)

    def test_negative_y_is_out_of_bounds(self):
        assert not self.board.in_bounds(0, -1)


class TestNeighbour:
    def setup_method(self):
        self.board = Board.empty(12, 12)

    def test_neighbour_north_decreases_y(self):
        assert self.board.neighbour(5, 5, Direction.NORTH) == (5, 4)

    def test_neighbour_south_increases_y(self):
        assert self.board.neighbour(5, 5, Direction.SOUTH) == (5, 6)

    def test_neighbour_east_increases_x(self):
        assert self.board.neighbour(5, 5, Direction.EAST) == (6, 5)

    def test_neighbour_west_decreases_x(self):
        assert self.board.neighbour(5, 5, Direction.WEST) == (4, 5)

    def test_neighbour_off_board_returns_none(self):
        assert self.board.neighbour(0, 0, Direction.NORTH) is None
        assert self.board.neighbour(0, 0, Direction.WEST) is None
        assert self.board.neighbour(11, 11, Direction.SOUTH) is None
        assert self.board.neighbour(11, 11, Direction.EAST) is None


class TestMovement:
    def setup_method(self):
        self.board = Board.empty(12, 12)

    def test_open_tile_allows_movement(self):
        assert self.board.can_move(5, 5, Direction.NORTH)
        assert self.board.can_move(5, 5, Direction.EAST)

    def test_wall_on_source_tile_blocks_movement(self):
        self.board.tile_at(5, 5).walls.add(Direction.NORTH)
        assert not self.board.can_move(5, 5, Direction.NORTH)

    def test_wall_on_destination_facing_side_blocks_movement(self):
        # Moving north from (5,5) → destination is (5,4); wall on south face of (5,4) blocks
        self.board.tile_at(5, 4).walls.add(Direction.SOUTH)
        assert not self.board.can_move(5, 5, Direction.NORTH)

    def test_wall_on_destination_other_side_does_not_block(self):
        # Wall on north face of (5,4) does not block entry from the south
        self.board.tile_at(5, 4).walls.add(Direction.NORTH)
        assert self.board.can_move(5, 5, Direction.NORTH)

    def test_moving_off_board_edge_is_blocked(self):
        assert not self.board.can_move(0, 0, Direction.NORTH)
        assert not self.board.can_move(0, 0, Direction.WEST)
        assert not self.board.can_move(11, 11, Direction.SOUTH)
        assert not self.board.can_move(11, 11, Direction.EAST)

    def test_walls_block_both_sides_of_an_edge(self):
        # A wall on the north face of (5,5) is a physical edge: it blocks
        # moving north OUT of (5,5) AND moving south INTO (5,5) from (5,4)
        self.board.tile_at(5, 5).walls.add(Direction.NORTH)
        assert not self.board.can_move(5, 5, Direction.NORTH)
        assert not self.board.can_move(5, 4, Direction.SOUTH)
        # But it doesn't block unrelated directions on (5,5)
        assert self.board.can_move(5, 5, Direction.EAST)


class TestBoardFromDict:
    def _minimal_dict(self, width=4, height=4, tiles=None):
        return {
            "name": "Test",
            "width": width,
            "height": height,
            "start_positions": [[0, 0], [1, 0]],
            "checkpoints": [[3, 3]],
            "tiles": tiles or [],
        }

    def test_loads_dimensions(self):
        board = Board.from_dict(self._minimal_dict())
        assert board.width == 4
        assert board.height == 4

    def test_loads_start_positions(self):
        board = Board.from_dict(self._minimal_dict())
        assert board.start_positions == [(0, 0), (1, 0)]

    def test_loads_checkpoints(self):
        board = Board.from_dict(self._minimal_dict())
        assert board.checkpoints == [(3, 3)]

    def test_unspecified_tiles_default_to_floor(self):
        board = Board.from_dict(self._minimal_dict())
        assert board.tile_at(2, 2).type == TileType.FLOOR

    def test_loads_pit_tile(self):
        data = self._minimal_dict(tiles=[{"x": 2, "y": 2, "type": "pit", "walls": []}])
        board = Board.from_dict(data)
        assert board.tile_at(2, 2).type == TileType.PIT

    def test_loads_conveyor_tile_with_direction(self):
        data = self._minimal_dict(tiles=[
            {"x": 1, "y": 1, "type": "conveyor", "direction": "north", "speed": 1, "walls": []}
        ])
        board = Board.from_dict(data)
        tile = board.tile_at(1, 1)
        assert tile.type == TileType.CONVEYOR
        assert tile.direction == Direction.NORTH
        assert tile.speed == 1

    def test_loads_express_conveyor_tile(self):
        data = self._minimal_dict(tiles=[
            {"x": 0, "y": 0, "type": "conveyor", "direction": "east", "speed": 2, "walls": []}
        ])
        board = Board.from_dict(data)
        assert board.tile_at(0, 0).speed == 2

    def test_loads_gear_tile(self):
        data = self._minimal_dict(tiles=[
            {"x": 2, "y": 1, "type": "gear", "rotation": "clockwise", "walls": []}
        ])
        board = Board.from_dict(data)
        tile = board.tile_at(2, 1)
        assert tile.type == TileType.GEAR
        assert tile.rotation == "clockwise"

    def test_loads_wall_on_tile(self):
        data = self._minimal_dict(tiles=[
            {"x": 1, "y": 1, "type": "floor", "walls": ["south", "east"]}
        ])
        board = Board.from_dict(data)
        tile = board.tile_at(1, 1)
        assert Direction.SOUTH in tile.walls
        assert Direction.EAST in tile.walls
        assert Direction.NORTH not in tile.walls

    def test_loads_checkpoint_tile_with_number(self):
        data = self._minimal_dict(tiles=[
            {"x": 3, "y": 3, "type": "checkpoint", "checkpoint_num": 1, "walls": []}
        ])
        board = Board.from_dict(data)
        tile = board.tile_at(3, 3)
        assert tile.type == TileType.CHECKPOINT
        assert tile.checkpoint_num == 1

    def test_loads_pusher_tile_with_active_registers(self):
        data = self._minimal_dict(tiles=[
            {"x": 0, "y": 2, "type": "pusher", "direction": "east",
             "active_registers": [1, 3, 5], "walls": ["west"]}
        ])
        board = Board.from_dict(data)
        tile = board.tile_at(0, 2)
        assert tile.type == TileType.PUSHER
        assert tile.active_registers == [1, 3, 5]
        assert tile.direction == Direction.EAST
