import { describe, expect, it } from 'vitest'
import { isConveyorActivationSubstep } from './conveyorActivation'

describe('isConveyorActivationSubstep', () => {
  it('is false for null/undefined and other substeps', () => {
    expect(isConveyorActivationSubstep(undefined)).toBe(false)
    expect(isConveyorActivationSubstep(null)).toBe(false)
    expect(isConveyorActivationSubstep('gears')).toBe(false)
    expect(isConveyorActivationSubstep('lasers')).toBe(false)
  })

  it('is true for express and normal conveyor substeps', () => {
    expect(isConveyorActivationSubstep('conveyors_express')).toBe(true)
    expect(isConveyorActivationSubstep('conveyors_normal')).toBe(true)
  })
})
