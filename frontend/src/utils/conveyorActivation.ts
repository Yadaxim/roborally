/** Matches backend `REGISTER_SUBSTEPS` conveyor ids in `game/activation.py`. */
export function isConveyorActivationSubstep(substepId: string | undefined | null): boolean {
  return substepId === 'conveyors_express' || substepId === 'conveyors_normal'
}
