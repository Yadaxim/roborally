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


class TestRoomLifecycle:
    def test_room_starts_in_lobby(self):
        room = Room("r1", simple_board())
        assert room.engine.phase == GamePhase.LOBBY

    def test_join_adds_player(self):
        room = Room("r1", simple_board())
        room.join("p1")
        assert "p1" in room.engine.robots

    def test_join_up_to_four_players(self):
        room = Room("r1", simple_board())
        for i in range(4):
            room.join(f"p{i}")
        assert len(room.engine.robots) == 4

    def test_join_fifth_player_raises(self):
        room = Room("r1", simple_board())
        for i in range(4):
            room.join(f"p{i}")
        with pytest.raises(RoomError):
            room.join("p5")

    def test_same_player_rejoin_does_not_duplicate(self):
        room = Room("r1", simple_board())
        room.join("p1")
        room.join("p1")
        assert len(room.engine.robots) == 1

    def test_start_game(self):
        room = Room("r1", simple_board())
        room.join("p1")
        room.start()
        assert room.engine.phase == GamePhase.PROGRAMMING

    def test_start_with_no_players_raises(self):
        room = Room("r1", simple_board())
        with pytest.raises(RoomError):
            room.start()


class TestRoomProgramming:
    def setup_method(self):
        self.room = Room("r1", simple_board())
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
        self.room = Room("r1", board)
        self.room.join("p1")
        self.room.start()
        hand = self.room.get_hand("p1")
        self.room.submit_registers("p1", hand[:5])

    def test_run_next_register_returns_events(self):
        events = self.room.run_next_register()
        assert isinstance(events, list)

    def test_run_all_registers_resets_to_programming(self):
        for _ in range(5):
            self.room.run_next_register()
        assert self.room.engine.phase == GamePhase.PROGRAMMING

    def test_run_register_outside_activation_raises(self):
        # exhaust activation first
        for _ in range(5):
            self.room.run_next_register()
        with pytest.raises(RoomError):
            self.room.run_next_register()


class TestRoomReconnect:
    def test_player_can_rejoin_after_game_starts(self):
        room = Room("r1", simple_board())
        room.join("p1")
        room.start()
        # Player disconnects and rejoins — should not raise, robot already exists
        room.join("p1")
        assert "p1" in room.engine.robots

    def test_reconnected_player_gets_same_robot(self):
        room = Room("r1", simple_board())
        room.join("p1")
        room.start()
        robot_before = room.engine.robots["p1"]
        room.join("p1")
        assert room.engine.robots["p1"] is robot_before
