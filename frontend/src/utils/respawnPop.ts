import type { Robot } from '../types/game'

/** Duration for scale-up after a robot becomes alive again (archive / respawn). */
export const RESPAWN_POP_MS = 380

/**
 * When a robot transitions from dead to alive, record `now` as the pop animation start.
 * Other keys are copied; callers may prune elsewhere.
 */
export function mergeRespawnPopStarts(
  prevStarts: Record<string, number>,
  prevRobots: Robot[],
  nextRobots: Robot[],
  now: number,
): Record<string, number> {
  const prevById = Object.fromEntries(prevRobots.map((r) => [r.id, r]))
  const out: Record<string, number> = { ...prevStarts }
  for (const r of nextRobots) {
    const p = prevById[r.id]
    if (p && !p.is_alive && r.is_alive) {
      out[r.id] = now
    }
  }
  return out
}
