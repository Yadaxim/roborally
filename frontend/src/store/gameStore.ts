import { create } from 'zustand'
import type { Card, Phase, Robot, ActivationEvent } from '../types/game'

interface GameState {
  // Connection
  connected: boolean
  playerId: string | null
  roomId: string | null

  // Game
  phase: Phase
  robots: Robot[]
  hand: Card[]
  registers: (Card | null)[]
  lockedCards: Record<number, Card>  // 1-based register number → retained card
  lastEvents: ActivationEvent[]
  winner: string | null
  dealTime: number | null

  // Actions
  setConnected: (v: boolean) => void
  setJoined: (playerId: string, roomId: string) => void
  setPhase: (phase: Phase) => void
  setRobots: (robots: Robot[]) => void
  setHand: (hand: Card[]) => void
  setDeal: (hand: Card[], lockedCards: Record<number, Card>) => void
  setRegister: (slot: number, card: Card | null) => void
  clearRegisters: () => void
  setLastEvents: (events: ActivationEvent[]) => void
  setWinner: (winner: string | null) => void
  applyStateSync: (phase: Phase, robots: Robot[], hand: Card[], lockedCards: Record<number, Card>) => void
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
  'connected' | 'playerId' | 'roomId' | 'phase' | 'robots' | 'hand' | 'registers' | 'lockedCards' | 'lastEvents' | 'winner' | 'dealTime'
> = {
  connected: false,
  playerId: null,
  roomId: null,
  phase: 'lobby',
  robots: [],
  hand: [],
  registers: [null, null, null, null, null],
  lockedCards: {},
  lastEvents: [],
  winner: null,
  dealTime: null,
}

export const useGameStore = create<GameState>((set) => ({
  ...INITIAL,

  setConnected: (connected) => set({ connected }),
  setJoined: (playerId, roomId) => set({ playerId, roomId }),
  setPhase: (phase) => set({ phase }),
  setRobots: (robots) => set({ robots }),
  setHand: (hand) => set({ hand, dealTime: Date.now() }),
  setDeal: (hand, lockedCards) => set({
    hand,
    lockedCards,
    registers: buildRegistersFromLocked(lockedCards),
    dealTime: Date.now(),
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
  setWinner: (winner) => set({ winner }),
  applyStateSync: (phase, robots, hand, lockedCards) => set({ phase, robots, hand, lockedCards }),
  reset: () => set(INITIAL),
}))
