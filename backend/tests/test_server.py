import json
import time
import pytest
from fastapi.testclient import TestClient

import server.main as server_main
from server.main import app


@pytest.fixture
def client():
    return TestClient(app)


def ws_send(ws, **kwargs):
    ws.send_text(json.dumps(kwargs))


def ws_recv(ws):
    return json.loads(ws.receive_text())


class TestHealth:
    def test_health_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestJoin:
    def test_join_creates_room_and_returns_joined(self, client):
        with client.websocket_connect("/ws") as ws:
            ws_send(ws, type="join", room_id="room1", player_id="alice")
            msg = ws_recv(ws)
            assert msg["type"] == "joined"
            assert msg["player_id"] == "alice"
            assert msg["room_id"] == "room1"

    def test_second_player_joins_same_room(self, client):
        with client.websocket_connect("/ws") as ws1:
            ws_send(ws1, type="join", room_id="room2", player_id="alice")
            ws_recv(ws1)  # joined
            with client.websocket_connect("/ws") as ws2:
                ws_send(ws2, type="join", room_id="room2", player_id="bob")
                msg = ws_recv(ws2)
                assert msg["type"] == "joined"
                assert msg["player_id"] == "bob"

    def test_unknown_command_returns_error(self, client):
        with client.websocket_connect("/ws") as ws:
            ws_send(ws, type="join", room_id="room_unk", player_id="p1")
            ws_recv(ws)  # joined
            ws_send(ws, type="invalid_command")
            msg = ws_recv(ws)
            assert msg["type"] == "error"


class TestStartGame:
    def test_start_broadcasts_game_started_and_deals_hand(self, client):
        with client.websocket_connect("/ws") as ws:
            ws_send(ws, type="join", room_id="start_room", player_id="p1")
            ws_recv(ws)  # joined
            ws_send(ws, type="start")
            msg1 = ws_recv(ws)  # game_started
            assert msg1["type"] == "game_started"
            assert len(msg1["robots"]) == 1
            msg2 = ws_recv(ws)  # phase_change
            assert msg2["type"] == "phase_change"
            assert msg2["phase"] == "programming"
            msg3 = ws_recv(ws)  # deal_hand
            assert msg3["type"] == "deal_hand"
            assert len(msg3["hand"]) == 9

    def test_start_with_no_players_returns_error(self, client):
        # start before joining — shouldn't happen normally, but test robustness
        with client.websocket_connect("/ws") as ws:
            ws_send(ws, type="join", room_id="empty_start", player_id="p1")
            ws_recv(ws)  # joined
            # Manually clear robots to simulate no-player state
            from server.main import _rooms
            _rooms["empty_start"].engine.robots.clear()
            ws_send(ws, type="start")
            msg = ws_recv(ws)
            assert msg["type"] == "error"


class TestSubmitRegisters:
    def _setup_programming(self, client, room_id, player_id):
        ws = client.websocket_connect("/ws").__enter__()
        ws_send(ws, type="join", room_id=room_id, player_id=player_id)
        ws_recv(ws)  # joined
        ws_send(ws, type="start")
        ws_recv(ws)  # game_started
        ws_recv(ws)  # phase_change programming
        hand_msg = ws_recv(ws)  # deal_hand
        return ws, hand_msg["hand"]

    def test_submit_five_cards_triggers_activation(self, client):
        with client.websocket_connect("/ws") as ws:
            ws_send(ws, type="join", room_id="submit1", player_id="p1")
            ws_recv(ws)
            ws_send(ws, type="start")
            ws_recv(ws)  # game_started
            ws_recv(ws)  # phase_change
            hand_msg = ws_recv(ws)  # deal_hand
            hand = hand_msg["hand"]
            ws_send(ws, type="submit_registers", cards=hand[:5])
            msg = ws_recv(ws)  # phase_change → activation
            assert msg["type"] == "phase_change"
            assert msg["phase"] == "activation"
            # Should receive 5 register_events
            for _ in range(5):
                ev_msg = ws_recv(ws)
                assert ev_msg["type"] == "register_events"

    def test_submit_wrong_count_returns_error(self, client):
        with client.websocket_connect("/ws") as ws:
            ws_send(ws, type="join", room_id="submit2", player_id="p1")
            ws_recv(ws)
            ws_send(ws, type="start")
            ws_recv(ws)
            ws_recv(ws)
            hand_msg = ws_recv(ws)
            hand = hand_msg["hand"]
            ws_send(ws, type="submit_registers", cards=hand[:3])
            msg = ws_recv(ws)
            assert msg["type"] == "error"


class TestReconnection:
    def test_rejoin_in_lobby_gets_joined_message(self, client):
        with client.websocket_connect("/ws") as ws1:
            ws_send(ws1, type="join", room_id="rejoin1", player_id="alice")
            ws_recv(ws1)  # joined
            # Alice disconnects and reconnects
        with client.websocket_connect("/ws") as ws2:
            ws_send(ws2, type="join", room_id="rejoin1", player_id="alice")
            msg = ws_recv(ws2)
            assert msg["type"] == "joined"

    def test_rejoin_during_programming_receives_state_sync(self, client):
        # Start a game, then reconnect and expect a state_sync message
        with client.websocket_connect("/ws") as ws1:
            ws_send(ws1, type="join", room_id="rejoin2", player_id="alice")
            ws_recv(ws1)  # joined
            ws_send(ws1, type="start")
            ws_recv(ws1)  # game_started
            ws_recv(ws1)  # phase_change programming
            ws_recv(ws1)  # deal_hand
        # Alice disconnects; reconnect
        with client.websocket_connect("/ws") as ws2:
            ws_send(ws2, type="join", room_id="rejoin2", player_id="alice")
            ws_recv(ws2)  # joined
            sync = ws_recv(ws2)
            assert sync["type"] == "state_sync"
            assert sync["phase"] == "programming"
            assert "robots" in sync
            assert "hand" in sync

    def test_rejoin_does_not_count_as_new_player(self, client):
        # Room with 1 player at max; same player rejoins — room stays at 1
        with client.websocket_connect("/ws") as ws1:
            ws_send(ws1, type="join", room_id="rejoin3", player_id="alice")
            ws_recv(ws1)
        # Reconnect
        with client.websocket_connect("/ws") as ws2:
            ws_send(ws2, type="join", room_id="rejoin3", player_id="alice")
            msg = ws_recv(ws2)
            assert msg["type"] == "joined"
            # Verify the room still has only 1 robot (alice's)
            assert len(server_main._rooms["rejoin3"].engine.robots) == 1


class TestProgrammingTimer:
    def test_timer_auto_submits_and_starts_activation(self, client, monkeypatch):
        monkeypatch.setattr(server_main, "PROGRAMMING_TIMEOUT", 0.05)
        with client.websocket_connect("/ws") as ws:
            ws_send(ws, type="join", room_id="timer1", player_id="p1")
            ws_recv(ws)  # joined
            ws_send(ws, type="start")
            ws_recv(ws)  # game_started
            ws_recv(ws)  # phase_change programming
            ws_recv(ws)  # deal_hand
            # Don't submit — let the timer fire
            time.sleep(0.3)
            msg = ws_recv(ws)
            assert msg["type"] == "phase_change"
            assert msg["phase"] == "activation"

    def test_timer_cancelled_when_all_submit_early(self, client, monkeypatch):
        monkeypatch.setattr(server_main, "PROGRAMMING_TIMEOUT", 0.3)
        with client.websocket_connect("/ws") as ws:
            ws_send(ws, type="join", room_id="timer2", player_id="p1")
            ws_recv(ws)  # joined
            ws_send(ws, type="start")
            ws_recv(ws)  # game_started
            ws_recv(ws)  # phase_change programming
            hand_msg = ws_recv(ws)  # deal_hand
            # Submit before timer expires
            ws_send(ws, type="submit_registers", cards=hand_msg["hand"][:5])
            msg = ws_recv(ws)  # phase_change activation
            assert msg["type"] == "phase_change"
            assert msg["phase"] == "activation"
            # Drain all 5 register_events
            for _ in range(5):
                ws_recv(ws)
            # Next round: get phase_change programming + deal_hand
            ws_recv(ws)  # phase_change programming
            ws_recv(ws)  # deal_hand
            # Wait past the original timer window — activation should NOT fire again
            time.sleep(0.4)
            # No more messages should arrive from the old timer
            ws.close()
