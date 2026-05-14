import type { ClientMessage, ServerMessage } from '../types/game'
import { useGameStore } from '../store/gameStore'

let socket: WebSocket | null = null

/**
 * Server fires phase_change→programming + deal_hand immediately after the last register_events,
 * while client animations take many seconds. Queue those messages until activation playback ends.
 */
const deferredActivationRound: ServerMessage[] = []

/** True while activation animations still need to run (queue or current register HUD). */
function activationPlaybackPending(): boolean {
  const s = useGameStore.getState()
  return (
    s.phase === 'activation'
    && (s.pendingRegisters.length > 0 || s.playbackHighlight !== null)
  )
}

/** Apply after the activation sequencer clears — safe to apply programming round messages. */
export function flushDeferredActivationMessages(): void {
  if (deferredActivationRound.length === 0) return
  const batch = deferredActivationRound.splice(0)
  for (const m of batch) {
    processServerMessage(m)
  }
}

function processServerMessage(msg: ServerMessage): void {
  const store = useGameStore.getState()
  switch (msg.type) {
    case 'room_list':
      store.setRooms(msg.rooms)
      break
    case 'joined':
      store.setJoined(
        msg.player_id,
        msg.room_id,
        msg.room_name,
        msg.is_host,
        msg.required_players,
        msg.board_id,
        msg.board_name,
      )
      break
    case 'roster_update':
      store.setLobbyPlayers(msg.players)
      break
    case 'player_ready':
      store.updateLobbyPlayerReady(msg.player_id, msg.is_ready)
      break
    case 'game_started':
      store.setRobots(msg.robots)
      store.setActiveBoard(msg.board)
      break
    case 'deal_hand':
      store.setDeal(msg.hand, msg.locked_cards, msg.programming_seconds_remaining)
      break
    case 'programming_timer':
      store.setProgrammingTimer(msg.programming_seconds_remaining)
      break
    case 'your_program':
      store.setRegistersFromProgram(msg.cards)
      break
    case 'phase_change':
      if (msg.phase === 'activation') {
        const regs = useGameStore.getState().registers
        store.setActivationProgramCards([...regs])
      }
      if (msg.phase === 'programming' && store.phase === 'activation') {
        store.setShowRoundResult(true)
      }
      store.setPhase(msg.phase)
      if (msg.phase === 'programming') {
        store.setPlaybackHighlight(null)
        store.setActivationProgramCards(null)
      }
      break
    case 'state_sync':
      store.applyStateSync(
        msg.phase,
        msg.robots,
        msg.hand,
        msg.locked_cards,
        msg.paused,
        msg.programming_seconds_remaining,
        msg.board,
      )
      break
    case 'game_paused':
      store.setGamePaused(msg.paused, msg.programming_seconds_remaining)
      break
    case 'board_updated':
      store.setLobbyBoard(msg.board_id, msg.board_name)
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

function dispatch(msg: ServerMessage): void {
  if (
    msg.type === 'phase_change'
    && msg.phase === 'programming'
    && activationPlaybackPending()
  ) {
    deferredActivationRound.push(msg)
    return
  }
  if (msg.type === 'deal_hand' && activationPlaybackPending()) {
    deferredActivationRound.push(msg)
    return
  }
  processServerMessage(msg)
}

export function connect(): void {
  const url = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`
  socket = new WebSocket(url)
  const store = useGameStore.getState()

  socket.onopen = () => {
    store.setConnected(true)
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
  deferredActivationRound.length = 0
  socket?.close()
}

export function send(msg: ClientMessage): void {
  if (socket?.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(msg))
  }
}
