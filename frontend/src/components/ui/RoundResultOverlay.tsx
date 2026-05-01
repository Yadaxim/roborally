import { useGameStore } from '../../store/gameStore'

const PLAYER_COLORS = ['#e63946', '#2a9d8f', '#e9c46a', '#f4a261']

export default function RoundResultOverlay() {
  const robots = useGameStore(s => s.robots)
  const playerId = useGameStore(s => s.playerId)
  const roundEvents = useGameStore(s => s.roundEvents)
  const show = useGameStore(s => s.showRoundResult)

  if (!show) return null

  function dismiss() {
    useGameStore.getState().setShowRoundResult(false)
  }

  const summaries = robots.map((robot, i) => {
    const events = roundEvents.filter(e => e.robot_id === robot.id)
    const damageTaken = events
      .filter(e => e.type === 'damage')
      .reduce((sum, e) => sum + (e.amount ?? 0), 0)
    const checkpoints = events
      .filter(e => e.type === 'checkpoint')
      .map(e => e.checkpoint_num as number)
    const destroyed = events.some(e => e.type === 'destroy')
    const color = PLAYER_COLORS[i % PLAYER_COLORS.length]
    return { robot, damageTaken, checkpoints, destroyed, color }
  })

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-gray-800 border border-gray-600 rounded-xl p-6 w-full max-w-md shadow-2xl">
        <h2 className="text-xl font-bold text-white mb-4 text-center tracking-wide">Round Complete</h2>

        <div className="flex flex-col gap-2 mb-6">
          {summaries.map(({ robot, damageTaken, checkpoints, destroyed, color }) => (
            <div
              key={robot.id}
              className={[
                'rounded p-3 bg-gray-700',
                robot.id === playerId ? 'ring-1 ring-indigo-400' : '',
              ].join(' ')}
            >
              <div className="flex items-center gap-2 mb-1.5">
                <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
                <span className="font-medium text-white">{robot.id}</span>
                {robot.id === playerId && <span className="text-xs text-indigo-400">(you)</span>}
              </div>

              <div className="flex flex-col gap-0.5 pl-4">
                {damageTaken > 0 && (
                  <span className="text-sm text-orange-400">💥 {damageTaken} damage taken</span>
                )}
                {destroyed && (
                  <span className="text-sm text-red-400">💀 Destroyed — respawning at archive</span>
                )}
                {checkpoints.map(n => (
                  <span key={n} className="text-sm text-yellow-400">🏁 Reached flag {n}!</span>
                ))}
                {damageTaken === 0 && !destroyed && checkpoints.length === 0 && (
                  <span className="text-sm text-gray-500">No events this round</span>
                )}
              </div>
            </div>
          ))}
        </div>

        <button
          className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded py-2 transition-colors"
          onClick={dismiss}
        >
          Continue →
        </button>
      </div>
    </div>
  )
}
