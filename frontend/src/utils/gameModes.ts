import type { GameMode } from '../types/game'

export const GAME_MODE_IDS: GameMode[] = [
  'standard',
  'king_of_the_hill',
  'capture_the_flag',
  'demolition_derby',
  'free_for_all',
]

const LABELS: Record<GameMode, string> = {
  standard: 'Standard race',
  king_of_the_hill: 'King of the Hill',
  capture_the_flag: 'Capture the Flag',
  demolition_derby: 'Demolition Derby',
  free_for_all: 'Free for All',
}

export const GAME_MODE_OPTIONS: { id: GameMode; label: string }[] = GAME_MODE_IDS.map(id => ({
  id,
  label: LABELS[id],
}))

export function gameModeLabel(mode: string): string {
  return LABELS[mode as GameMode] ?? mode.replace(/_/g, ' ')
}

export function asGameMode(raw: string | undefined): GameMode {
  if (raw && GAME_MODE_IDS.includes(raw as GameMode)) return raw as GameMode
  return 'standard'
}
