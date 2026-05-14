import pytest

from game.board import Board, Direction, TileType
from game.engine import GamePhase
from server.rooms import Room, RoomError


def simple_board() -> Board:
    board = Board.empty(12, 12)
    board.start_positions = [(i, 0) for i in range(4)]
    board.tile_at(2, 2).type = TileType.CHECKPOINT
    board.tile_at(2, 2).checkpoint_num = 1
    board.checkpoints = [(2, 2)]
    return board


def room_bundle() -> tuple[Board, str, dict]:
    b = simple_board()
    d = {
        "name": "Test",
        "width": 12,
        "height": 12,
        "start_positions": [list(p) for p in b.start_positions],
        "checkpoints": [list(p) for p in b.checkpoints],
        "tiles": [{"x": 2, "y": 2, "type": "checkpoint", "checkpoint_num": 1, "walls": []}],
    }
    return b, "test", d


class TestRoomLifecycle:
    def test_room_starts_in_lobby(self):
        room = Room("r1", *room_bundle())
        assert room.engine.phase == GamePhase.LOBBY

    def test_join_adds_player(self):
        room = Room("r1", *room_bundle())
        room.join("p1")
        assert "p1" in room.engine.robots

    def test_join_up_to_four_players(self):
        room = Room("r1", *room_bundle())
        for i in range(4):
            room.join(f"p{i}")
        assert len(room.engine.robots) == 4

    def test_join_fifth_player_raises(self):
        room = Room("r1", *room_bundle())
        for i in range(4):
            room.join(f"p{i}")
        with pytest.raises(RoomError):
            room.join("p5")

    def test_same_player_rejoin_does_not_duplicate(self):
        room = Room("r1", *room_bundle())
        room.join("p1")
        room.join("p1")
        assert len(room.engine.robots) == 1

    def test_start_game(self):
        room = Room("r1", *room_bundle())
        room.join("p1")
        room.start()
        assert room.engine.phase == GamePhase.PROGRAMMING

    def test_start_with_no_players_raises(self):
        room = Room("r1", *room_bundle())
        with pytest.raises(RoomError):
            room.start()

    def test_can_force_start_with_one_player(self):
        room = Room("r1", *room_bundle(), required_players=1)
        room.join("p1")
        assert room.can_force_start is True

    def test_all_ready_true_when_solo_ready(self):
        room = Room("r1", *room_bundle(), required_players=1)
        room.join("solo")
        assert room.all_ready is False
        room.set_ready("solo", True)
        assert room.all_ready is True


class TestRoomProgramming:
    def setup_method(self):
        self.room = Room("r1", *room_bundle())
        self.room.join("p1")
        self.room.join("p2")
        self.room.start()

    def test_get_hand_returns_cards(self):
        hand = self.room.get_hand("p1")
        assert len(hand) == 9

    def test_submit_registers_accepted(self):
        hand = self.room.get_hand("p1")
        self.room.submit_registers("p1", hand[:5])
        assert self.room.engine.registers["p1"] is not None

    def test_submit_wrong_count_raises(self):
        hand = self.room.get_hand("p1")
        with pytest.raises(RoomError):
            self.room.submit_registers("p1", hand[:3])

    def test_submit_card_not_in_hand_raises(self):
        from game.cards import Card, CardType
        hand = self.room.get_hand("p1")
        bad = Card(type=CardType.MOVE_3, priority=9999)
        with pytest.raises(RoomError):
            self.room.submit_registers("p1", hand[:4] + [bad])

    def test_all_submitted_transitions_to_activation(self):
        h1 = self.room.get_hand("p1")
        h2 = self.room.get_hand("p2")
        self.room.submit_registers("p1", h1[:5])
        assert self.room.engine.phase == GamePhase.PROGRAMMING
        self.room.submit_registers("p2", h2[:5])
        assert self.room.engine.phase == GamePhase.ACTIVATION


class TestRoomActivation:
    def setup_method(self):
        # No checkpoints so the game can't end mid-test
        board = Board.empty(12, 12)
        board.start_positions = [(5, 5)]
        bd = {"name": "Act", "width": 12, "height": 12, "start_positions": [[5, 5]], "checkpoints": [], "tiles": []}
        self.room = Room("r1", board, "act", bd)
        self.room.join("p1")
        self.room.start()
        hand = self.room.get_hand("p1")
        self.room.submit_registers("p1", hand[:5])

    def test_run_next_activation_substep_returns_tuple(self):
        _reg, key, idx, events = self.room.run_next_activation_substep()
        assert isinstance(events, list)
        assert isinstance(key, str)
        assert 1 <= idx <= 8

    def test_run_all_registers_resets_to_programming(self):
        for _ in range(5 * 8):
            self.room.run_next_activation_substep()
        assert self.room.engine.phase == GamePhase.PROGRAMMING

    def test_run_register_outside_activation_raises(self):
        # exhaust activation first
        for _ in range(5 * 8):
            self.room.run_next_activation_substep()
        with pytest.raises(RoomError):
            self.room.run_next_activation_substep()



class TestRoomReplaceBoard:
    def test_replace_lobby_board_reseats_robots(self):
        room = Room("r1", *room_bundle())
        room.join("a")
        room.join("b")
        board2 = Board.empty(12, 12)
        board2.start_positions = [(10, 10), (10, 9)]
        bd2 = {
            "name": "Other",
            "width": 12,
            "height": 12,
            "start_positions": [[10, 10], [10, 9]],
            "checkpoints": [],
            "tiles": [],
        }
        room.replace_lobby_board(board2, "other", bd2)
        assert room.board_id == "other"
        assert (room.engine.robots["a"].x, room.engine.robots["a"].y) == (10, 10)
        assert (room.engine.robots["b"].x, room.engine.robots["b"].y) == (10, 9)
        assert room.ready["a"] is False


class TestRoomReconnect:
    def test_player_can_rejoin_after_game_starts(self):
        room = Room("r1", *room_bundle())
        room.join("p1")
        room.start()
        # Player disconnects and rejoins — should not raise, robot already exists
        room.join("p1")
        assert "p1" in room.engine.robots

    def test_reconnected_player_gets_same_robot(self):
        room = Room("r1", *room_bundle())
        room.join("p1")
        room.start()
        robot_before = room.engine.robots["p1"]
        room.join("p1")
        assert room.engine.robots["p1"] is robot_before
