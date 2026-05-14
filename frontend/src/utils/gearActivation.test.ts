import { describe, expect, it } from 'vitest'
import { isGearsActivationSubstep } from './gearActivation'

describe('isGearsActivationSubstep', () => {
  it('is false for null/undefined and other substeps', () => {
    expect(isGearsActivationSubstep(undefined)).toBe(false)
    expect(isGearsActivationSubstep(null)).toBe(false)
    expect(isGearsActivationSubstep('conveyors_normal')).toBe(false)
  })

  it('is true for gears substep', () => {
    expect(isGearsActivationSubstep('gears')).toBe(true)
  })
})
