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
  lastEvents: ActivationEvent[]
  winner: string | null

  // Actions
  setConnected: (v: boolean) => void
  setJoined: (playerId: string, roomId: string) => void
  setPhase: (phase: Phase) => void
  setRobots: (robots: Robot[]) => void
  setHand: (hand: Card[]) => void
  setRegister: (slot: number, card: Card | null) => void
  clearRegisters: () => void
  setLastEvents: (events: ActivationEvent[]) => void
  setWinner: (winner: string | null) => void
  applyStateSync: (phase: Phase, robots: Robot[], hand: Card[]) => void
  reset: () => void
}

const INITIAL: Pick<
  GameState,
  'connected' | 'playerId' | 'roomId' | 'phase' | 'robots' | 'hand' | 'registers' | 'lastEvents' | 'winner'
> = {
  connected: false,
  playerId: null,
  roomId: null,
  phase: 'lobby',
  robots: [],
  hand: [],
  registers: [null, null, null, null, null],
  lastEvents: [],
  winner: null,
}

export const useGameStore = create<GameState>((set) => ({
  ...INITIAL,

  setConnected: (connected) => set({ connected }),
  setJoined: (playerId, roomId) => set({ playerId, roomId }),
  setPhase: (phase) => set({ phase }),
  setRobots: (robots) => set({ robots }),
  setHand: (hand) => set({ hand }),
  setRegister: (slot, card) =>
    set((s) => {
      const registers = [...s.registers]
      registers[slot] = card
      return { registers }
    }),
  clearRegisters: () => set({ registers: [null, null, null, null, null] }),
  setLastEvents: (lastEvents) => set({ lastEvents }),
  setWinner: (winner) => set({ winner }),
  applyStateSync: (phase, robots, hand) => set({ phase, robots, hand }),
  reset: () => set(INITIAL),
}))
