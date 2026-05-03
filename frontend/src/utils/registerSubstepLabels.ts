/** Matches backend `REGISTER_SUBSTEPS` ids in `game/activation.py`. */
export const REGISTER_SUBSTEP_LABELS: Record<string, string> = {
  program_cards: 'Program cards',
  conveyors_express: 'Express conveyors',
  conveyors_normal: 'Normal conveyors',
  pushers: 'Push panels',
  gears: 'Gears',
  crushers: 'Crushers',
  lasers: 'Lasers',
  checkpoints: 'Checkpoints & repair',
}

export function labelForSubstepId(id: string): string {
  return REGISTER_SUBSTEP_LABELS[id] ?? id.replace(/_/g, ' ')
}
