import { describe, expect, it } from 'vitest'
import { asGameMode, gameModeLabel } from './gameModes'

describe('asGameMode', () => {
  it('defaults invalid or missing to standard', () => {
    expect(asGameMode(undefined)).toBe('standard')
    expect(asGameMode('')).toBe('standard')
    expect(asGameMode('nope')).toBe('standard')
  })

  it('accepts known modes', () => {
    expect(asGameMode('demolition_derby')).toBe('demolition_derby')
    expect(asGameMode('king_of_the_hill')).toBe('king_of_the_hill')
  })
})

describe('gameModeLabel', () => {
  it('formats unknown snake_case', () => {
    expect(gameModeLabel('foo_bar')).toBe('foo bar')
  })
})
