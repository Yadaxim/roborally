import { beforeEach, describe, expect, it } from 'vitest'
import { useGameStore } from './gameStore'

beforeEach(() => useGameStore.getState().reset())

describe('initial state', () => {
  it('starts in lobby phase', () => {
    expect(useGameStore.getState().phase).toBe('lobby')
  })

  it('has empty registers', () => {
    expect(useGameStore.getState().registers).toEqual([null, null, null, null, null])
  })
})

describe('setJoined', () => {
  it('stores player and room ids', () => {
    useGameStore.getState().setJoined('alice', 'room1')
    const s = useGameStore.getState()
    expect(s.playerId).toBe('alice')
    expect(s.roomId).toBe('room1')
  })
})

describe('setRegister', () => {
  it('places a card in the correct slot', () => {
    const card = { type: 'move_1' as const, priority: 100 }
    useGameStore.getState().setRegister(2, card)
    expect(useGameStore.getState().registers[2]).toEqual(card)
  })

  it('does not affect other slots', () => {
    const card = { type: 'move_1' as const, priority: 100 }
    useGameStore.getState().setRegister(0, card)
    const regs = useGameStore.getState().registers
    expect(regs[1]).toBeNull()
    expect(regs[4]).toBeNull()
  })
})

describe('clearRegisters', () => {
  it('resets all slots to null', () => {
    const card = { type: 'move_2' as const, priority: 200 }
    const store = useGameStore.getState()
    store.setRegister(0, card)
    store.setRegister(3, card)
    store.clearRegisters()
    expect(useGameStore.getState().registers).toEqual([null, null, null, null, null])
  })
})

describe('applyStateSync', () => {
  it('updates phase, robots, and hand together', () => {
    const robots = [{ id: 'alice', x: 1, y: 2, facing: 'north' as const, damage: 0, lives: 3, checkpoints_touched: 0, is_alive: true }]
    const hand = [{ type: 'move_1' as const, priority: 500 }]
    useGameStore.getState().applyStateSync('programming', robots, hand)
    const s = useGameStore.getState()
    expect(s.phase).toBe('programming')
    expect(s.robots).toEqual(robots)
    expect(s.hand).toEqual(hand)
  })
})

describe('setWinner', () => {
  it('stores the winner', () => {
    useGameStore.getState().setWinner('alice')
    expect(useGameStore.getState().winner).toBe('alice')
  })
})

describe('reset', () => {
  it('returns to initial state', () => {
    useGameStore.getState().setJoined('bob', 'room99')
    useGameStore.getState().setPhase('activation')
    useGameStore.getState().reset()
    const s = useGameStore.getState()
    expect(s.playerId).toBeNull()
    expect(s.phase).toBe('lobby')
  })
})
