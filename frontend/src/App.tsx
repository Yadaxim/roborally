import { useState } from 'react'
import { useGameStore } from './store/gameStore'
import { connect, send, disconnect } from './ws/client'
import Scene from './components/game/Scene'
import ProgrammingPanel from './components/ui/ProgrammingPanel'
import PlayerPanel from './components/ui/PlayerPanel'
import './index.css'

const PLAYER_COLORS = ['#e63946', '#2a9d8f', '#e9c46a', '#f4a261']

export default function App() {
  const { phase, connected, playerId, roomId, winner, robots } = useGameStore()
  const [roomInput, setRoomInput] = useState('')
  const [playerInput, setPlayerInput] = useState('')

  function handleJoin() {
    if (!roomInput.trim() || !playerInput.trim()) return
    connect(roomInput.trim(), playerInput.trim())
  }

  function handleStart() {
    send({ type: 'start' })
  }

  function handlePlayAgain() {
    useGameStore.getState().reset()
    disconnect()
  }

  // ── Game over ──────────────────────────────────────────────────────────────
  if (phase === 'game_over') {
    const sorted = [...robots].sort(
      (a, b) => b.checkpoints_touched - a.checkpoints_touched || a.damage - b.damage
    )
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-6 bg-gray-900 text-white p-8">
        <h1 className="text-5xl font-bold text-yellow-400 tracking-wide">Game Over</h1>

        {winner && (
          <p className="text-2xl text-white">
            Winner: <span className="font-bold text-indigo-300">{winner}</span>
          </p>
        )}

        {/* Standings */}
        <div className="flex flex-col gap-2 w-full max-w-sm">
          {sorted.map((r, i) => (
            <div key={r.id} className="flex items-center gap-3 bg-gray-800 rounded px-4 py-2">
              <div
                className="w-3 h-3 rounded-full flex-shrink-0"
                style={{ backgroundColor: PLAYER_COLORS[robots.indexOf(r) % PLAYER_COLORS.length] }}
              />
              <span className="flex-1 font-medium">{r.id}</span>
              <span className="text-yellow-400 text-sm">{r.checkpoints_touched} flags</span>
              <span className="text-gray-400 text-sm">dmg {r.damage}</span>
              {i === 0 && winner && <span className="text-yellow-300 text-xs font-bold">WIN</span>}
            </div>
          ))}
        </div>

        <button
          className="mt-2 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded px-6 py-2"
          onClick={handlePlayAgain}
        >
          Play Again
        </button>
      </div>
    )
  }

  // ── Lobby ──────────────────────────────────────────────────────────────────
  if (!connected || phase === 'lobby') {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-4 p-8 bg-gray-900 text-white">
        <h1 className="text-4xl font-bold text-indigo-400">RoboRally</h1>
        <div className="flex flex-col gap-2 w-full max-w-sm">
          <input
            className="bg-gray-800 border border-gray-600 rounded px-3 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500"
            placeholder="Room ID"
            value={roomInput}
            onChange={(e) => setRoomInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleJoin()}
          />
          <input
            className="bg-gray-800 border border-gray-600 rounded px-3 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500"
            placeholder="Your name"
            value={playerInput}
            onChange={(e) => setPlayerInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleJoin()}
          />
          <button
            className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded px-4 py-2 disabled:opacity-40"
            disabled={!roomInput.trim() || !playerInput.trim()}
            onClick={handleJoin}
          >
            Join / Create Room
          </button>
        </div>
        {connected && (
          <div className="flex flex-col items-center gap-3 mt-2">
            <p className="text-gray-400 text-sm">Joined as <span className="text-white">{playerId}</span> in <span className="text-white">{roomId}</span></p>
            <button
              className="bg-green-600 hover:bg-green-500 text-white font-semibold rounded px-6 py-2"
              onClick={handleStart}
            >
              Start Game
            </button>
          </div>
        )}
      </div>
    )
  }

  // ── In-game ────────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col h-screen bg-gray-900 text-white">
      <header className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700 flex-shrink-0">
        <span className="font-bold text-indigo-400">RoboRally</span>
        <span className="text-sm text-gray-400 capitalize">
          {phase === 'programming' ? 'Programming' : phase === 'activation' ? 'Activation' : phase}
        </span>
        <span className="text-sm text-gray-500">{roomId}</span>
      </header>

      <div className="flex-1 flex overflow-hidden">
        <div className="relative flex-1">
          <Scene />
        </div>
        <PlayerPanel />
      </div>

      {phase === 'programming' && <ProgrammingPanel />}
    </div>
  )
}
