/** Duration the client keeps the robot visible while it sinks into the floor. */
export const DESTROY_SINK_MS = 320

export function nextDestroySinkUntil(
  prev: Record<string, number>,
  robotId: string,
  now: number,
  durationMs: number = DESTROY_SINK_MS,
): Record<string, number> {
  return { ...prev, [robotId]: now + durationMs }
}

export function pruneExpiredDestroySinks(
  sinks: Record<string, number>,
  now: number,
): Record<string, number> {
  const out: Record<string, number> = {}
  for (const [id, until] of Object.entries(sinks)) {
    if (until > now) out[id] = until
  }
  return out
}
