import type { ClientMessage, ServerMessage } from '../types/game'
import { useGameStore } from '../store/gameStore'

let socket: WebSocket | null = null

export function connect(): void {
  const url = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`
  socket = new WebSocket(url)
  const store = useGameStore.getState()

  socket.onopen = () => {
    store.setConnected(true)
    // Server sends room_list automatically on connect
  }

  socket.onclose = () => {
    store.setConnected(false)
    socket = null
  }

  socket.onmessage = (ev) => {
    const msg: ServerMessage = JSON.parse(ev.data as string)
    dispatch(msg)
  }
}

export function disconnect(): void {
  socket?.close()
}

export function send(msg: ClientMessage): void {
  if (socket?.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(msg))
  }
}

function dispatch(msg: ServerMessage): void {
  const store = useGameStore.getState()
  switch (msg.type) {
    case 'room_list':
      store.setRooms(msg.rooms)
      break
    case 'joined':
      store.setJoined(msg.player_id, msg.room_id, msg.room_name, msg.is_host, msg.required_players)
      break
    case 'roster_update':
      store.setLobbyPlayers(msg.players)
      break
    case 'player_ready':
      store.updateLobbyPlayerReady(msg.player_id, msg.is_ready)
      break
    case 'game_started':
      store.setRobots(msg.robots)
      break
    case 'deal_hand':
      store.setDeal(msg.hand, msg.locked_cards)
      break
    case 'phase_change':
      if (msg.phase === 'programming' && store.phase === 'activation') {
        store.setShowRoundResult(true)
      }
      store.setPhase(msg.phase)
      break
    case 'state_sync':
      store.applyStateSync(msg.phase, msg.robots, msg.hand, msg.locked_cards)
      break
    case 'register_events':
      store.enqueueRegister(msg)
      break
    case 'game_over':
      store.setPhase('game_over')
      store.setWinner(msg.winner)
      break
    case 'error':
      console.error('[ws]', msg.message)
      break
  }
}
