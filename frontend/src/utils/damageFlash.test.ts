import { describe, expect, it } from 'vitest'
import {
  DAMAGE_FLASH_DURATION_MS,
  nextDamageFlashUntil,
  pruneExpiredFlashes,
} from './damageFlash'

describe('nextDamageFlashUntil', () => {
  it('records flash end time for a robot', () => {
    const out = nextDamageFlashUntil({}, 'alice', 10_000)
    expect(out.alice).toBe(10_000 + DAMAGE_FLASH_DURATION_MS)
  })

  it('preserves other robots', () => {
    const prev = { bob: 11_000 }
    const out = nextDamageFlashUntil(prev, 'alice', 10_000)
    expect(out.bob).toBe(11_000)
    expect(out.alice).toBe(10_000 + DAMAGE_FLASH_DURATION_MS)
  })

  it('accepts custom duration', () => {
    const out = nextDamageFlashUntil({}, 'x', 1000, 200)
    expect(out.x).toBe(1200)
  })
})

describe('pruneExpiredFlashes', () => {
  it('removes ended flashes', () => {
    const out = pruneExpiredFlashes({ a: 500, b: 1500 }, 1000)
    expect(out).toEqual({ b: 1500 })
  })

  it('returns empty when all expired', () => {
    expect(pruneExpiredFlashes({ a: 100 }, 200)).toEqual({})
  })
})
