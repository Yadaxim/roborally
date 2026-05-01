import type { ClientMessage, ServerMessage } from '../types/game'
import { useGameStore } from '../store/gameStore'

let socket: WebSocket | null = null

export function connect(roomId: string, playerId: string): void {
  const url = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`
  socket = new WebSocket(url)
  const store = useGameStore.getState()

  socket.onopen = () => {
    store.setConnected(true)
    send({ type: 'join', room_id: roomId, player_id: playerId })
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
    case 'joined':
      store.setJoined(msg.player_id, msg.room_id)
      break
    case 'game_started':
      store.setRobots(msg.robots)
      break
    case 'deal_hand':
      store.setDeal(msg.hand, msg.locked_cards)
      break
    case 'phase_change':
      store.setPhase(msg.phase)
      break
    case 'state_sync':
      store.applyStateSync(msg.phase, msg.robots, msg.hand, msg.locked_cards)
      break
    case 'register_events':
      store.setRobots(msg.robots)
      store.setLastEvents(msg.events)
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
