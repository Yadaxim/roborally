import { describe, expect, it } from 'vitest'
import { DESTROY_SINK_MS, nextDestroySinkUntil, pruneExpiredDestroySinks } from './destroySink'

describe('nextDestroySinkUntil', () => {
  it('schedules sink end time', () => {
    const out = nextDestroySinkUntil({}, 'r1', 5000)
    expect(out.r1).toBe(5000 + DESTROY_SINK_MS)
  })

  it('keeps other robots', () => {
    const prev = { r2: 9000 }
    const out = nextDestroySinkUntil(prev, 'r1', 5000)
    expect(out.r2).toBe(9000)
    expect(out.r1).toBe(5000 + DESTROY_SINK_MS)
  })
})

describe('pruneExpiredDestroySinks', () => {
  it('drops finished sinks', () => {
    expect(pruneExpiredDestroySinks({ a: 100, b: 500 }, 400)).toEqual({ b: 500 })
  })
})
