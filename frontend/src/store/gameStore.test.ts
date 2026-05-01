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
    const robots = [{ id: 'alice', x: 1, y: 2, facing: 'north' as const, damage: 0, lives: 3, checkpoints_touched: 0, is_alive: true, locked_registers: [] }]
    const hand = [{ type: 'move_1' as const, priority: 500 }]
    useGameStore.getState().applyStateSync('programming', robots, hand, {})
    const s = useGameStore.getState()
    expect(s.phase).toBe('programming')
    expect(s.robots).toEqual(robots)
    expect(s.hand).toEqual(hand)
  })
})

describe('setDeal', () => {
  it('sets hand and clears unlocked register slots', () => {
    const card = { type: 'move_1' as const, priority: 100 }
    useGameStore.getState().setRegister(0, card)
    useGameStore.getState().setDeal([card], {})
    const s = useGameStore.getState()
    expect(s.hand).toEqual([card])
    expect(s.registers).toEqual([null, null, null, null, null])
  })

  it('pre-populates locked register slots with retained cards', () => {
    const locked = { type: 'turn_right' as const, priority: 200 }
    useGameStore.getState().setDeal([], { 5: locked })
    const s = useGameStore.getState()
    expect(s.registers[4]).toEqual(locked)   // slot 4 = register 5
    expect(s.lockedCards).toEqual({ 5: locked })
  })

  it('leaves non-locked slots null', () => {
    const locked = { type: 'turn_right' as const, priority: 200 }
    useGameStore.getState().setDeal([], { 5: locked })
    const regs = useGameStore.getState().registers
    expect(regs[0]).toBeNull()
    expect(regs[3]).toBeNull()
  })
})

describe('setRegister with locked slots', () => {
  it('ignores writes to locked slots', () => {
    const lockedCard = { type: 'turn_right' as const, priority: 200 }
    useGameStore.getState().setDeal([], { 3: lockedCard })
    const newCard = { type: 'move_1' as const, priority: 100 }
    useGameStore.getState().setRegister(2, newCard)  // slot 2 = register 3 (locked)
    expect(useGameStore.getState().registers[2]).toEqual(lockedCard)
  })
})

describe('clearRegisters with locked slots', () => {
  it('retains locked cards when clearing', () => {
    const lockedCard = { type: 'turn_right' as const, priority: 200 }
    useGameStore.getState().setDeal([], { 5: lockedCard })
    useGameStore.getState().clearRegisters()
    const regs = useGameStore.getState().registers
    expect(regs[4]).toEqual(lockedCard)
    expect(regs[0]).toBeNull()
  })
})

describe('setWinner', () => {
  it('stores the winner', () => {
    useGameStore.getState().setWinner('alice')
    expect(useGameStore.getState().winner).toBe('alice')
  })
})

describe('appendRoundEvents', () => {
  it('accumulates events across multiple calls', () => {
    const e1 = { type: 'damage' as const, robot_id: 'alice', amount: 1 }
    const e2 = { type: 'checkpoint' as const, robot_id: 'bob', checkpoint_num: 1 }
    useGameStore.getState().appendRoundEvents([e1])
    useGameStore.getState().appendRoundEvents([e2])
    expect(useGameStore.getState().roundEvents).toEqual([e1, e2])
  })

  it('is cleared by setDeal', () => {
    const e = { type: 'damage' as const, robot_id: 'alice', amount: 1 }
    useGameStore.getState().appendRoundEvents([e])
    useGameStore.getState().setDeal([], {})
    expect(useGameStore.getState().roundEvents).toEqual([])
  })
})

describe('showRoundResult', () => {
  it('starts false', () => {
    expect(useGameStore.getState().showRoundResult).toBe(false)
  })

  it('can be toggled', () => {
    useGameStore.getState().setShowRoundResult(true)
    expect(useGameStore.getState().showRoundResult).toBe(true)
    useGameStore.getState().setShowRoundResult(false)
    expect(useGameStore.getState().showRoundResult).toBe(false)
  })

  it('is cleared by setDeal', () => {
    useGameStore.getState().setShowRoundResult(true)
    useGameStore.getState().setDeal([], {})
    expect(useGameStore.getState().showRoundResult).toBe(false)
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
