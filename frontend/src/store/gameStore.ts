import { create } from 'zustand'
import type { Card, Phase, Robot, ActivationEvent, PendingRegister, RoomSummary, LobbyPlayer } from '../types/game'

interface GameState {
  // Connection
  connected: boolean
  playerId: string | null
  roomId: string | null

  // Lobby
  rooms: RoomSummary[]
  lobbyPlayers: LobbyPlayer[]
  isHost: boolean
  roomName: string
  requiredPlayers: number

  // Game
  phase: Phase
  robots: Robot[]
  hand: Card[]
  registers: (Card | null)[]
  lockedCards: Record<number, Card>
  lastEvents: ActivationEvent[]
  roundEvents: ActivationEvent[]
  showRoundResult: boolean
  winner: string | null
  dealTime: number | null

  // Animation queue
  pendingRegisters: PendingRegister[]

  // Actions
  setConnected: (v: boolean) => void
  setJoined: (playerId: string, roomId: string, roomName: string, isHost: boolean, requiredPlayers: number) => void
  setRooms: (rooms: RoomSummary[]) => void
  setLobbyPlayers: (players: LobbyPlayer[]) => void
  updateLobbyPlayerReady: (playerId: string, isReady: boolean) => void
  setPhase: (phase: Phase) => void
  setRobots: (robots: Robot[]) => void
  updateRobot: (id: string, updates: Partial<Robot>) => void
  setHand: (hand: Card[]) => void
  setDeal: (hand: Card[], lockedCards: Record<number, Card>) => void
  setRegister: (slot: number, card: Card | null) => void
  clearRegisters: () => void
  setLastEvents: (events: ActivationEvent[]) => void
  appendRoundEvents: (events: ActivationEvent[]) => void
  setShowRoundResult: (show: boolean) => void
  setWinner: (winner: string | null) => void
  applyStateSync: (phase: Phase, robots: Robot[], hand: Card[], lockedCards: Record<number, Card>) => void
  enqueueRegister: (msg: PendingRegister) => void
  dequeueRegister: () => PendingRegister | null
  reset: () => void
}

function buildRegistersFromLocked(lockedCards: Record<number, Card>): (Card | null)[] {
  const registers: (Card | null)[] = [null, null, null, null, null]
  for (const [regNum, card] of Object.entries(lockedCards)) {
    registers[Number(regNum) - 1] = card
  }
  return registers
}

const INITIAL: Pick<
  GameState,
  | 'connected' | 'playerId' | 'roomId'
  | 'rooms' | 'lobbyPlayers' | 'isHost' | 'roomName' | 'requiredPlayers'
  | 'phase' | 'robots' | 'hand' | 'registers' | 'lockedCards'
  | 'lastEvents' | 'roundEvents' | 'showRoundResult' | 'winner' | 'dealTime' | 'pendingRegisters'
> = {
  connected: false,
  playerId: null,
  roomId: null,
  rooms: [],
  lobbyPlayers: [],
  isHost: false,
  roomName: '',
  requiredPlayers: 2,
  phase: 'lobby',
  robots: [],
  hand: [],
  registers: [null, null, null, null, null],
  lockedCards: {},
  lastEvents: [],
  roundEvents: [],
  showRoundResult: false,
  winner: null,
  dealTime: null,
  pendingRegisters: [],
}

export const useGameStore = create<GameState>((set) => ({
  ...INITIAL,

  setConnected: (connected) => set({ connected }),
  setJoined: (playerId, roomId, roomName, isHost, requiredPlayers) =>
    set({ playerId, roomId, roomName, isHost, requiredPlayers }),
  setRooms: (rooms) => set({ rooms }),
  setLobbyPlayers: (lobbyPlayers) => set({ lobbyPlayers }),
  updateLobbyPlayerReady: (playerId, isReady) =>
    set((s) => ({
      lobbyPlayers: s.lobbyPlayers.map(p =>
        p.player_id === playerId ? { ...p, is_ready: isReady } : p
      ),
    })),
  setPhase: (phase) => set({ phase }),
  setRobots: (robots) => set({ robots }),
  updateRobot: (id, updates) =>
    set((s) => ({ robots: s.robots.map(r => r.id === id ? { ...r, ...updates } : r) })),
  setHand: (hand) => set({ hand, dealTime: Date.now() }),
  setDeal: (hand, lockedCards) => set({
    hand,
    lockedCards,
    registers: buildRegistersFromLocked(lockedCards),
    dealTime: Date.now(),
    roundEvents: [],
    showRoundResult: false,
  }),
  setRegister: (slot, card) =>
    set((s) => {
      const regNum = slot + 1
      if (regNum in s.lockedCards) return {}
      const registers = [...s.registers]
      registers[slot] = card
      return { registers }
    }),
  clearRegisters: () =>
    set((s) => ({ registers: buildRegistersFromLocked(s.lockedCards) })),
  setLastEvents: (lastEvents) => set({ lastEvents }),
  appendRoundEvents: (events) =>
    set((s) => ({ roundEvents: [...s.roundEvents, ...events] })),
  setShowRoundResult: (showRoundResult) => set({ showRoundResult }),
  setWinner: (winner) => set({ winner }),
  applyStateSync: (phase, robots, hand, lockedCards) => set({ phase, robots, hand, lockedCards }),
  enqueueRegister: (msg) => set((s) => ({ pendingRegisters: [...s.pendingRegisters, msg] })),
  dequeueRegister: () => {
    let result: PendingRegister | null = null
    useGameStore.setState((s) => {
      if (s.pendingRegisters.length === 0) return {}
      const [first, ...rest] = s.pendingRegisters
      result = first
      return { pendingRegisters: rest }
    })
    return result
  },
  reset: () => set(INITIAL),
}))
