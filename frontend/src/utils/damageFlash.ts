/** Wall-clock duration for the red damage hit flash (matches activation pacing). */
export const DAMAGE_FLASH_DURATION_MS = 420

/**
 * Schedule a damage flash for `robotId` so it decays linearly from `now` until `now + duration`.
 */
export function nextDamageFlashUntil(
  prev: Record<string, number>,
  robotId: string,
  now: number,
  durationMs: number = DAMAGE_FLASH_DURATION_MS,
): Record<string, number> {
  return { ...prev, [robotId]: now + durationMs }
}

/** Drop entries whose flash has already ended (keeps the map small). */
export function pruneExpiredFlashes(
  flashes: Record<string, number>,
  now: number,
): Record<string, number> {
  const out: Record<string, number> = {}
  for (const [id, until] of Object.entries(flashes)) {
    if (until > now) out[id] = until
  }
  return out
}
