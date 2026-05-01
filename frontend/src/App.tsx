import { useState } from 'react'
import { useGameStore } from './store/gameStore'
import { connect, send } from './ws/client'
import Scene from './components/game/Scene'
import './index.css'

export default function App() {
  const { phase, connected, playerId, roomId, hand, registers, winner } = useGameStore()
  const [roomInput, setRoomInput] = useState('')
  const [playerInput, setPlayerInput] = useState('')

  function handleJoin() {
    if (!roomInput.trim() || !playerInput.trim()) return
    connect(roomInput.trim(), playerInput.trim())
  }

  function handleStart() {
    send({ type: 'start' })
  }

  function handleSubmit() {
    const cards = registers.filter(Boolean) as NonNullable<(typeof registers)[number]>[]
    if (cards.length === 5) send({ type: 'submit_registers', cards })
  }

  if (phase === 'game_over') {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-4">
        <h1 className="text-4xl font-bold text-yellow-400">Game Over</h1>
        <p className="text-xl">{winner ? `Winner: ${winner}` : 'No winner'}</p>
      </div>
    )
  }

  if (!connected || phase === 'lobby') {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-4 p-8">
        <h1 className="text-4xl font-bold text-indigo-400">RoboRally</h1>
        <div className="flex flex-col gap-2 w-full max-w-sm">
          <input
            className="bg-gray-800 border border-gray-600 rounded px-3 py-2 text-white"
            placeholder="Room ID"
            value={roomInput}
            onChange={(e) => setRoomInput(e.target.value)}
          />
          <input
            className="bg-gray-800 border border-gray-600 rounded px-3 py-2 text-white"
            placeholder="Your name"
            value={playerInput}
            onChange={(e) => setPlayerInput(e.target.value)}
          />
          <button
            className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded px-4 py-2"
            onClick={handleJoin}
          >
            Join / Create Room
          </button>
        </div>
        {connected && (
          <button
            className="mt-4 bg-green-600 hover:bg-green-500 text-white font-semibold rounded px-6 py-2"
            onClick={handleStart}
          >
            Start Game
          </button>
        )}
      </div>
    )
  }

  return (
    <div className="flex flex-col h-screen bg-gray-900 text-white">
      <header className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700">
        <span className="font-bold text-indigo-400">RoboRally</span>
        <span className="text-sm text-gray-400">
          {playerId} · {roomId} · {phase}
        </span>
      </header>

      <div className="flex-1 relative">
        <Scene />
      </div>

      {phase === 'programming' && (
        <div className="bg-gray-800 border-t border-gray-700 p-3 flex flex-col gap-2">
          <div className="flex gap-2 items-end">
            {registers.map((c, i) => (
              <div
                key={i}
                className="w-16 h-20 border-2 border-dashed border-gray-500 rounded flex items-center justify-center text-xs text-center text-gray-400 cursor-pointer hover:border-red-400"
                onClick={() => useGameStore.getState().setRegister(i, null)}
              >
                {c ? (
                  <span className="font-mono text-white">
                    {c.type}
                    <br />
                    {c.priority}
                  </span>
                ) : (
                  `Reg ${i + 1}`
                )}
              </div>
            ))}
            <button
              className="ml-auto bg-green-700 hover:bg-green-600 text-white rounded px-4 py-2 font-semibold disabled:opacity-40"
              disabled={registers.filter(Boolean).length !== 5}
              onClick={handleSubmit}
            >
              Confirm
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {hand.map((c, i) => (
              <button
                key={i}
                className="bg-gray-700 hover:bg-gray-600 rounded px-3 py-2 text-sm font-mono"
                onClick={() => {
                  const slot = registers.findIndex((r) => r === null)
                  if (slot !== -1) useGameStore.getState().setRegister(slot, c)
                }}
              >
                {c.type} / {c.priority}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
