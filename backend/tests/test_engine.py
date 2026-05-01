import pytest

from game.board import Board, Direction, TileType
from game.cards import Card, CardType
from game.engine import GameEngine, GamePhase
from game.robot import Robot


def make_board_with_checkpoints(n: int) -> Board:
    board = Board.empty(12, 12)
    for i in range(n):
        x, y = 2 + i * 2, 2
        board.tile_at(x, y).type = TileType.CHECKPOINT
        board.tile_at(x, y).checkpoint_num = i + 1
        board.checkpoints.append((x, y))
    return board


def card(type, priority=500):
    return Card(type=type, priority=priority)


class TestGamePhases:
    def test_initial_phase_is_lobby(self):
        board = Board.empty(12, 12)
        engine = GameEngine(board)
        assert engine.phase == GamePhase.LOBBY

    def test_add_player_in_lobby(self):
        board = Board.empty(12, 12)
        board.start_positions = [(0, 0), (1, 0)]
        engine = GameEngine(board)
        engine.add_player("p1")
        assert "p1" in engine.robots

    def test_cannot_add_player_outside_lobby(self):
        board = Board.empty(12, 12)
        board.start_positions = [(0, 0), (1, 0)]
        engine = GameEngine(board)
        engine.add_player("p1")
        engine.start_game()
        with pytest.raises(RuntimeError):
            engine.add_player("p2")

    def test_start_game_requires_at_least_one_player(self):
        board = Board.empty(12, 12)
        engine = GameEngine(board)
        with pytest.raises(RuntimeError):
            engine.start_game()

    def test_start_game_moves_to_programming(self):
        board = Board.empty(12, 12)
        board.start_positions = [(0, 0)]
        engine = GameEngine(board)
        engine.add_player("p1")
        engine.start_game()
        assert engine.phase == GamePhase.PROGRAMMING

    def test_player_placed_at_start_position(self):
        board = Board.empty(12, 12)
        board.start_positions = [(3, 4)]
        engine = GameEngine(board)
        engine.add_player("p1")
        engine.start_game()
        robot = engine.robots["p1"]
        assert (robot.x, robot.y) == (3, 4)


class TestProgrammingPhase:
    def setup_method(self):
        self.board = Board.empty(12, 12)
        self.board.start_positions = [(0, 0), (2, 0)]
        self.engine = GameEngine(self.board)
        self.engine.add_player("p1")
        self.engine.add_player("p2")
        self.engine.start_game()

    def test_players_receive_hands(self):
        assert len(self.engine.hands["p1"]) == 9
        assert len(self.engine.hands["p2"]) == 9

    def test_submit_registers_accepted(self):
        hand = self.engine.hands["p1"]
        self.engine.submit_registers("p1", hand[:5])
        assert self.engine.registers["p1"] is not None

    def test_submit_wrong_number_of_registers_raises(self):
        hand = self.engine.hands["p1"]
        with pytest.raises(ValueError):
            self.engine.submit_registers("p1", hand[:3])

    def test_submit_card_not_in_hand_raises(self):
        hand = self.engine.hands["p1"]
        fake_card = Card(type=CardType.MOVE_3, priority=9999)
        with pytest.raises(ValueError):
            self.engine.submit_registers("p1", hand[:4] + [fake_card])

    def test_all_submitted_advances_to_activation(self):
        h1 = self.engine.hands["p1"]
        h2 = self.engine.hands["p2"]
        self.engine.submit_registers("p1", h1[:5])
        assert self.engine.phase == GamePhase.PROGRAMMING
        self.engine.submit_registers("p2", h2[:5])
        assert self.engine.phase == GamePhase.ACTIVATION

    def test_submit_while_not_in_programming_raises(self):
        self.engine.phase = GamePhase.LOBBY
        hand = self.engine.hands["p1"]
        with pytest.raises(RuntimeError):
            self.engine.submit_registers("p1", hand[:5])


class TestActivationPhase:
    def setup_method(self):
        self.board = Board.empty(12, 12)
        self.board.start_positions = [(5, 5)]
        self.engine = GameEngine(self.board)
        self.engine.add_player("p1")
        self.engine.start_game()

    def _program_and_activate(self, cards_5):
        hand = self.engine.hands["p1"]
        # Use actual hand cards for first few, then fill remaining with provided
        # We need to give specific cards — just submit the 5 given cards after
        # patching the hand to include them
        self.engine.hands["p1"] = cards_5 + list(self.engine.hands["p1"])[:4]
        self.engine.submit_registers("p1", cards_5)

    def test_execute_next_register_runs_one_register(self):
        hand = self.engine.hands["p1"]
        self.engine.submit_registers("p1", hand[:5])
        events = self.engine.execute_next_register()
        assert isinstance(events, list)
        assert self.engine.current_register == 2

    def _safe_registers(self) -> list[Card]:
        """Five rotation cards — robot won't move, so it can't fall off the board."""
        cards = [Card(type=CardType.TURN_RIGHT, priority=100 + i) for i in range(5)]
        self.engine.hands["p1"] = cards + list(self.engine.hands["p1"])[:4]
        return cards

    def test_execute_all_registers_returns_to_programming(self):
        self.engine.submit_registers("p1", self._safe_registers())
        for _ in range(5):
            self.engine.execute_next_register()
        assert self.engine.phase == GamePhase.PROGRAMMING

    def test_execute_register_outside_activation_raises(self):
        with pytest.raises(RuntimeError):
            self.engine.execute_next_register()

    def test_new_round_deals_fresh_hands(self):
        self.engine.submit_registers("p1", self._safe_registers())
        for _ in range(5):
            self.engine.execute_next_register()
        hand2 = self.engine.hands["p1"]
        assert hand2 is not None
        assert len(hand2) == 9


class TestWinCondition:
    def test_touching_all_checkpoints_triggers_game_over(self):
        board = make_board_with_checkpoints(2)
        board.start_positions = [(2, 3)]
        engine = GameEngine(board)
        engine.add_player("p1")
        engine.start_game()
        robot = engine.robots["p1"]
        # Manually place at cp1 and advance
        robot.x, robot.y = 2, 2
        robot.checkpoints_touched = 0
        engine._check_win_condition()
        assert engine.phase != GamePhase.GAME_OVER  # cp1 only, not winner yet
        robot.checkpoints_touched = 2  # touched both
        engine._check_win_condition()
        assert engine.phase == GamePhase.GAME_OVER

    def test_winner_is_recorded(self):
        board = make_board_with_checkpoints(1)
        board.start_positions = [(2, 3)]
        engine = GameEngine(board)
        engine.add_player("p1")
        engine.start_game()
        engine.robots["p1"].checkpoints_touched = 1
        engine._check_win_condition()
        assert engine.winner == "p1"

    def test_no_winner_when_none_finished(self):
        board = make_board_with_checkpoints(2)
        board.start_positions = [(0, 0)]
        engine = GameEngine(board)
        engine.add_player("p1")
        engine.start_game()
        engine._check_win_condition()
        assert engine.winner is None
        assert engine.phase != GamePhase.GAME_OVER

    def test_win_checked_after_each_register(self):
        board = make_board_with_checkpoints(1)
        cx, cy = board.checkpoints[0]
        board.start_positions = [(cx, cy + 1)]
        engine = GameEngine(board)
        engine.add_player("p1")
        engine.start_game()
        hand = engine.hands["p1"]
        # Make robot face north and submit MOVE_1 as first register
        engine.robots["p1"].facing = Direction.NORTH
        engine.submit_registers("p1", hand[:5])
        # Find a MOVE_1 in the submitted registers and force it to first slot
        engine.registers["p1"] = [card(CardType.MOVE_1)] + list(hand[1:5])
        engine.execute_next_register()
        assert engine.phase == GamePhase.GAME_OVER

    def test_all_robots_eliminated_causes_game_over(self):
        board = make_board_with_checkpoints(1)
        board.start_positions = [(0, 0)]
        engine = GameEngine(board)
        engine.add_player("p1")
        engine.start_game()
        engine.robots["p1"].lives = 0
        engine.robots["p1"]._alive = False
        engine._check_win_condition()
        assert engine.phase == GamePhase.GAME_OVER
