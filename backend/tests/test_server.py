import json
import pytest
from fastapi.testclient import TestClient

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
