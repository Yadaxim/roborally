import json
import time
import pytest
from contextlib import contextmanager
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


@contextmanager
def connected_ws(client):
    """Open a WebSocket and consume the initial room_list message."""
    with client.websocket_connect("/ws") as ws:
        ws_recv(ws)  # room_list
        yield ws


class TestHealth:
    def test_health_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestRoomList:
    def test_room_list_sent_on_connect(self, client):
        with client.websocket_connect("/ws") as ws:
            msg = ws_recv(ws)
            assert msg["type"] == "room_list"
            assert "rooms" in msg

    def test_room_list_http_endpoint(self, client):
        resp = client.get("/rooms")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestJoin:
    def test_join_creates_room_and_returns_joined(self, client):
        with connected_ws(client) as ws:
            ws_send(ws, type="join", room_id="room1", player_id="alice")
            msg = ws_recv(ws)
            assert msg["type"] == "joined"
            assert msg["player_id"] == "alice"
            assert msg["room_id"] == "room1"

    def test_second_player_joins_same_room(self, client):
        with connected_ws(client) as ws1:
            ws_send(ws1, type="join", room_id="room2", player_id="alice")
            ws_recv(ws1)  # joined
            with connected_ws(client) as ws2:
                ws_send(ws2, type="join", room_id="room2", player_id="bob")
                msg = ws_recv(ws2)
                assert msg["type"] == "joined"
                assert msg["player_id"] == "bob"

    def test_unknown_command_returns_error(self, client):
        with connected_ws(client) as ws:
            ws_send(ws, type="join", room_id="room_unk", player_id="p1")
            ws_recv(ws)  # joined
            ws_send(ws, type="invalid_command")
            msg = ws_recv(ws)
            assert msg["type"] == "error"


class TestLobby:
    def test_create_room_returns_joined_with_host(self, client):
        with connected_ws(client) as ws:
            ws_send(ws, type="create_room", player_name="alice", room_name="My Room", required_players=2)
            msg = ws_recv(ws)
            assert msg["type"] == "joined"
            assert msg["player_id"] == "alice"
            assert msg["room_name"] == "My Room"
            assert msg["is_host"] is True
            assert msg["required_players"] == 2
            assert "room_id" in msg

    def test_create_room_sends_roster_update(self, client):
        with connected_ws(client) as ws:
            ws_send(ws, type="create_room", player_name="alice", room_name="R", required_players=2)
            ws_recv(ws)  # joined
            roster = ws_recv(ws)
            assert roster["type"] == "roster_update"
            assert len(roster["players"]) == 1
            assert roster["players"][0]["player_id"] == "alice"
            assert roster["players"][0]["is_host"] is True
            assert roster["players"][0]["is_ready"] is False

    def test_join_room_joins_existing(self, client):
        with connected_ws(client) as ws1:
            ws_send(ws1, type="create_room", player_name="alice", room_name="Test", required_players=2)
            joined1 = ws_recv(ws1)
            ws_recv(ws1)  # roster_update (alice)
            room_id = joined1["room_id"]

            with connected_ws(client) as ws2:
                ws_send(ws2, type="join_room", player_name="bob", room_id=room_id)
                joined2 = ws_recv(ws2)
                assert joined2["type"] == "joined"
                assert joined2["player_id"] == "bob"
                assert joined2["is_host"] is False
                ws_recv(ws2)  # roster_update (bob's copy)
                # alice should receive a roster update too
                roster = ws_recv(ws1)
                assert roster["type"] == "roster_update"
                assert len(roster["players"]) == 2

    def test_join_room_not_found_returns_error(self, client):
        with connected_ws(client) as ws:
            ws_send(ws, type="join_room", player_name="alice", room_id="XXXX")
            msg = ws_recv(ws)
            assert msg["type"] == "error"

    def test_ready_toggle_broadcasts_player_ready(self, client):
        with connected_ws(client) as ws1:
            ws_send(ws1, type="create_room", player_name="alice", room_name="R2", required_players=2)
            joined = ws_recv(ws1)
            ws_recv(ws1)  # roster
            room_id = joined["room_id"]

            with connected_ws(client) as ws2:
                ws_send(ws2, type="join_room", player_name="bob", room_id=room_id)
                ws_recv(ws2)  # joined
                ws_recv(ws2)  # roster
                ws_recv(ws1)  # roster update (bob joined)

                # Bob marks ready
                ws_send(ws2, type="ready", value=True)
                msg = ws_recv(ws2)
                assert msg["type"] == "player_ready"
                assert msg["player_id"] == "bob"
                assert msg["is_ready"] is True
                # Alice should also receive it
                msg2 = ws_recv(ws1)
                assert msg2["type"] == "player_ready"

    def test_all_ready_starts_game(self, client):
        with connected_ws(client) as ws1:
            ws_send(ws1, type="create_room", player_name="alice", room_name="AutoStart", required_players=2)
            joined = ws_recv(ws1)
            ws_recv(ws1)  # roster
            room_id = joined["room_id"]

            with connected_ws(client) as ws2:
                ws_send(ws2, type="join_room", player_name="bob", room_id=room_id)
                ws_recv(ws2)  # joined
                ws_recv(ws2)  # roster
                ws_recv(ws1)  # roster (bob joined)

                ws_send(ws1, type="ready", value=True)
                ws_recv(ws1)  # player_ready alice
                ws_recv(ws2)  # player_ready alice

                ws_send(ws2, type="ready", value=True)
                ws_recv(ws1)  # player_ready bob
                ws_recv(ws2)  # player_ready bob

                # Both ready → game starts automatically
                msg = ws_recv(ws1)
                assert msg["type"] == "game_started"

    def test_force_start_by_host(self, client):
        with connected_ws(client) as ws1:
            ws_send(ws1, type="create_room", player_name="alice", room_name="ForceTest", required_players=3)
            joined = ws_recv(ws1)
            ws_recv(ws1)  # roster
            room_id = joined["room_id"]

            with connected_ws(client) as ws2:
                ws_send(ws2, type="join_room", player_name="bob", room_id=room_id)
                ws_recv(ws2)  # joined
                ws_recv(ws2)  # roster
                ws_recv(ws1)  # roster (bob joined)

                # Force start (only 2 of 3 required, but >= MIN_PLAYERS_TO_START)
                ws_send(ws1, type="force_start")
                msg = ws_recv(ws1)
                assert msg["type"] == "game_started"

    def test_force_start_by_non_host_returns_error(self, client):
        with connected_ws(client) as ws1:
            ws_send(ws1, type="create_room", player_name="alice", room_name="FT2", required_players=2)
            joined = ws_recv(ws1)
            ws_recv(ws1)  # roster
            room_id = joined["room_id"]

            with connected_ws(client) as ws2:
                ws_send(ws2, type="join_room", player_name="bob", room_id=room_id)
                ws_recv(ws2)  # joined
                ws_recv(ws2)  # roster
                ws_recv(ws1)  # roster

                ws_send(ws2, type="force_start")
                msg = ws_recv(ws2)
                assert msg["type"] == "error"

    def test_created_room_appears_in_room_list(self, client):
        with connected_ws(client) as ws:
            ws_send(ws, type="create_room", player_name="alice", room_name="Visible Room", required_players=2)
            ws_recv(ws)  # joined
            ws_recv(ws)  # roster

        # A new client should see the room in their room_list
        with client.websocket_connect("/ws") as ws2:
            msg = ws_recv(ws2)
            assert msg["type"] == "room_list"
            room_names = [r["room_name"] for r in msg["rooms"]]
            assert "Visible Room" in room_names


class TestStartGame:
    def test_start_broadcasts_game_started_and_deals_hand(self, client):
        with connected_ws(client) as ws:
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
        with connected_ws(client) as ws:
            ws_send(ws, type="join", room_id="empty_start", player_id="p1")
            ws_recv(ws)  # joined
            from server.main import _rooms
            _rooms["empty_start"].engine.robots.clear()
            ws_send(ws, type="start")
            msg = ws_recv(ws)
            assert msg["type"] == "error"


class TestSubmitRegisters:
    def _setup_programming(self, client, room_id, player_id):
        ws_cm = client.websocket_connect("/ws")
        ws = ws_cm.__enter__()
        ws_recv(ws)  # room_list
        ws_send(ws, type="join", room_id=room_id, player_id=player_id)
        ws_recv(ws)  # joined
        ws_send(ws, type="start")
        ws_recv(ws)  # game_started
        ws_recv(ws)  # phase_change programming
        hand_msg = ws_recv(ws)  # deal_hand
        return ws, hand_msg["hand"]

    def test_submit_five_cards_triggers_activation(self, client):
        with connected_ws(client) as ws:
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
        with connected_ws(client) as ws:
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
        with connected_ws(client) as ws1:
            ws_send(ws1, type="join", room_id="rejoin1", player_id="alice")
            ws_recv(ws1)  # joined
        with connected_ws(client) as ws2:
            ws_send(ws2, type="join", room_id="rejoin1", player_id="alice")
            msg = ws_recv(ws2)
            assert msg["type"] == "joined"

    def test_rejoin_during_programming_receives_state_sync(self, client):
        with connected_ws(client) as ws1:
            ws_send(ws1, type="join", room_id="rejoin2", player_id="alice")
            ws_recv(ws1)  # joined
            ws_send(ws1, type="start")
            ws_recv(ws1)  # game_started
            ws_recv(ws1)  # phase_change programming
            ws_recv(ws1)  # deal_hand
        with connected_ws(client) as ws2:
            ws_send(ws2, type="join", room_id="rejoin2", player_id="alice")
            ws_recv(ws2)  # joined
            sync = ws_recv(ws2)
            assert sync["type"] == "state_sync"
            assert sync["phase"] == "programming"
            assert "robots" in sync
            assert "hand" in sync

    def test_rejoin_does_not_count_as_new_player(self, client):
        with connected_ws(client) as ws1:
            ws_send(ws1, type="join", room_id="rejoin3", player_id="alice")
            ws_recv(ws1)
        with connected_ws(client) as ws2:
            ws_send(ws2, type="join", room_id="rejoin3", player_id="alice")
            msg = ws_recv(ws2)
            assert msg["type"] == "joined"
            assert len(server_main._rooms["rejoin3"].engine.robots) == 1


class TestProgrammingTimer:
    def test_timer_auto_submits_and_starts_activation(self, client, monkeypatch):
        monkeypatch.setattr(server_main, "PROGRAMMING_TIMEOUT", 0.05)
        with connected_ws(client) as ws:
            ws_send(ws, type="join", room_id="timer1", player_id="p1")
            ws_recv(ws)  # joined
            ws_send(ws, type="start")
            ws_recv(ws)  # game_started
            ws_recv(ws)  # phase_change programming
            ws_recv(ws)  # deal_hand
            time.sleep(0.3)
            msg = ws_recv(ws)
            assert msg["type"] == "phase_change"
            assert msg["phase"] == "activation"

    def test_timer_cancelled_when_all_submit_early(self, client, monkeypatch):
        monkeypatch.setattr(server_main, "PROGRAMMING_TIMEOUT", 0.3)
        with connected_ws(client) as ws:
            ws_send(ws, type="join", room_id="timer2", player_id="p1")
            ws_recv(ws)  # joined
            ws_send(ws, type="start")
            ws_recv(ws)  # game_started
            ws_recv(ws)  # phase_change programming
            hand_msg = ws_recv(ws)  # deal_hand
            ws_send(ws, type="submit_registers", cards=hand_msg["hand"][:5])
            msg = ws_recv(ws)  # phase_change activation
            assert msg["type"] == "phase_change"
            assert msg["phase"] == "activation"
            for _ in range(5):
                ws_recv(ws)
            ws_recv(ws)  # phase_change programming
            ws_recv(ws)  # deal_hand
            time.sleep(0.4)
            ws.close()
