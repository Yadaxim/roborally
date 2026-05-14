/** Matches backend `REGISTER_SUBSTEPS` gears id in `game/activation.py`. */
export function isGearsActivationSubstep(substepId: string | undefined | null): boolean {
  return substepId === 'gears'
}
