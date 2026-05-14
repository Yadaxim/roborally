import { describe, expect, it } from 'vitest'
import type { Robot } from '../types/game'
import { mergeRespawnPopStarts } from './respawnPop'

function makeRobot(id: string, alive: boolean): Robot {
  return {
    id,
    x: 1,
    y: 2,
    facing: 'north',
    damage: 0,
    lives: 3,
    checkpoints_touched: 0,
    is_alive: alive,
    locked_registers: [],
  }
}

describe('mergeRespawnPopStarts', () => {
  it('records start time when a robot revives', () => {
    const prev = [makeRobot('a', false)]
    const next = [makeRobot('a', true)]
    const out = mergeRespawnPopStarts({}, prev, next, 12_000)
    expect(out.a).toBe(12_000)
  })

  it('does nothing when alive state unchanged', () => {
    const prev = [makeRobot('a', true)]
    const next = [makeRobot('a', true)]
    const out = mergeRespawnPopStarts({ a: 5000 }, prev, next, 12_000)
    expect(out.a).toBe(5000)
  })

  it('does nothing when still dead', () => {
    const prev = [makeRobot('a', false)]
    const next = [makeRobot('a', false)]
    const out = mergeRespawnPopStarts({}, prev, next, 12_000)
    expect(out).toEqual({})
  })
})
