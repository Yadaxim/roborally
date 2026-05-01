import { useGameStore } from '../../store/gameStore'
import { DIZZY_HIGHWAY } from '../../data/dizzyHighway'
import type { ActivationEvent } from '../../types/game'

const PLAYER_COLORS = ['#e63946', '#2a9d8f', '#e9c46a', '#f4a261']
const MAX_HEALTH = 9
const TOTAL_CHECKPOINTS = DIZZY_HIGHWAY.checkpoints.length

function EventLine({ event }: { event: ActivationEvent }) {
  if (event.type === 'damage') {
    return (
      <div className="text-xs text-orange-400 truncate">
        {event.robot_id} -{event.amount} hp
      </div>
    )
  }
  if (event.type === 'destroy') {
    return <div className="text-xs text-red-400 truncate">{event.robot_id} destroyed</div>
  }
  if (event.type === 'checkpoint') {
    return (
      <div className="text-xs text-yellow-400 truncate">
        {event.robot_id} flag {event.checkpoint_num}
      </div>
    )
  }
  return null
}

export default function PlayerPanel() {
  const robots = useGameStore(s => s.robots)
  const playerId = useGameStore(s => s.playerId)
  const lastEvents = useGameStore(s => s.lastEvents)

  const significant = lastEvents.filter(
    e => e.type === 'damage' || e.type === 'destroy' || e.type === 'checkpoint'
  )

  return (
    <div className="w-48 bg-gray-800 border-l border-gray-700 flex flex-col overflow-hidden flex-shrink-0">
      <div className="flex-1 overflow-y-auto p-2 flex flex-col gap-2">
        {robots.map((robot, i) => {
          const color = PLAYER_COLORS[i % PLAYER_COLORS.length]
          const health = MAX_HEALTH - robot.damage
          const isMe = robot.id === playerId

          return (
            <div
              key={robot.id}
              className={[
                'rounded p-2 bg-gray-700',
                isMe ? 'ring-1 ring-indigo-400' : '',
                !robot.is_alive ? 'opacity-50' : '',
              ].join(' ')}
            >
              {/* Name row */}
              <div className="flex items-center gap-1.5 mb-2">
                <div
                  className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                  style={{ backgroundColor: color }}
                />
                <span className="text-xs font-medium text-white truncate flex-1">
                  {robot.id}
                </span>
                {isMe && <span className="text-xs text-indigo-400">you</span>}
              </div>

              {/* Health bar */}
              <div className="flex gap-0.5 mb-2">
                {Array.from({ length: MAX_HEALTH }, (_, j) => (
                  <div
                    key={j}
                    className={`h-1.5 flex-1 rounded-sm ${j < health ? 'bg-green-400' : 'bg-gray-600'}`}
                  />
                ))}
              </div>

              {/* Lives + checkpoint flags */}
              <div className="flex items-center justify-between">
                <span className="text-xs text-red-400 tracking-tight">
                  {'♥'.repeat(Math.max(0, robot.lives))}
                </span>
                <div className="flex gap-0.5">
                  {Array.from({ length: TOTAL_CHECKPOINTS }, (_, j) => (
                    <div
                      key={j}
                      className={`w-2 h-2 rounded-full ${j < robot.checkpoints_touched ? 'bg-yellow-400' : 'bg-gray-600'}`}
                    />
                  ))}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Recent event log */}
      {significant.length > 0 && (
        <div className="border-t border-gray-700 p-2 flex flex-col gap-0.5 max-h-20 overflow-y-auto">
          {significant.slice(-5).map((e, i) => (
            <EventLine key={i} event={e} />
          ))}
        </div>
      )}
    </div>
  )
}
