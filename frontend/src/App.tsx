import { useEffect, useState } from 'react'
import { useGameStore } from './store/gameStore'
import { proposePlayerName, proposeRoomName } from './utils/proposedNames'
import { gameModeLabel } from './utils/gameModes'
import ModeSelector from './components/ui/ModeSelector'
import { connect, send, disconnect } from './ws/client'
import type { ClientMessage, GameMode } from './types/game'
import { useAnimationSequencer } from './hooks/useAnimationSequencer'
import Scene from './components/game/Scene'
import ProgrammingPanel from './components/ui/ProgrammingPanel'
import PlayerPanel from './components/ui/PlayerPanel'
import RoundResultOverlay from './components/ui/RoundResultOverlay'
import ActivationPlaybackHud from './components/ui/ActivationPlaybackHud'
import './index.css'

const PLAYER_COLORS = ['#e63946', '#2a9d8f', '#e9c46a', '#f4a261']

export default function App() {
  const { phase, connected, playerId, roomId, roomName, isHost, requiredPlayers, rooms, lobbyPlayers, robots, winner, gamePaused, lobbyBoardId, lobbyBoardName, lobbyGameMode } =
    useGameStore()
  const [playerName, setPlayerName] = useState(() => proposePlayerName())
  const [createRoomName, setCreateRoomName] = useState('')
  const [createRequired, setCreateRequired] = useState(2)
  const [createBoardId, setCreateBoardId] = useState('dizzy_highway')
  const [createGameMode, setCreateGameMode] = useState<GameMode>('standard')
  const [availableBoards, setAvailableBoards] = useState<{ id: string; name: string }[]>([])
  useAnimationSequencer()

  useEffect(() => {
    if (!connected || roomId) return
    fetch('/boards')
      .then(r => r.json())
      .then((data: { id: string; name: string }[]) => setAvailableBoards(Array.isArray(data) ? data : []))
      .catch(() => setAvailableBoards([]))
  }, [connected, roomId])

  useEffect(() => {
    if (!connected || !roomId || phase !== 'lobby') return
    fetch('/boards')
      .then(r => r.json())
      .then((data: { id: string; name: string }[]) => setAvailableBoards(Array.isArray(data) ? data : []))
      .catch(() => setAvailableBoards([]))
  }, [connected, roomId, phase])

  /** Room title avoids lobby name clashes; player name only refills when cleared (quirky + random suffix). */
  useEffect(() => {
    if (!connected || roomId) return
    setPlayerName(prev => (prev.trim() ? prev : proposePlayerName()))
    setCreateRoomName(prev => {
      const trimmed = prev.trim()
      const takenRoomNames = new Set(rooms.map(r => r.room_name.toLowerCase()))
      if (!trimmed) return proposeRoomName(rooms)
      if (!takenRoomNames.has(trimmed.toLowerCase())) return prev
      return proposeRoomName(rooms)
    })
  }, [connected, roomId, rooms])

  const myLobbyPlayer = lobbyPlayers.find(p => p.player_id === playerId)
  const isReady = myLobbyPlayer?.is_ready ?? false
  const readyCount = lobbyPlayers.filter(p => p.is_ready).length

  function handleConnect() {
    if (!playerName.trim()) return
    connect()
  }

  function handleCreateRoom() {
    if (!createRoomName.trim()) return
    send({
      type: 'create_room',
      player_name: playerName.trim(),
      room_name: createRoomName.trim(),
      required_players: createRequired,
      board_id: createBoardId,
      game_mode: createGameMode,
    })
    setCreateRoomName('')
  }

  function handleJoinRoom(rid: string) {
    send({ type: 'join_room', player_name: playerName.trim(), room_id: rid })
  }

  function handleToggleReady() {
    send({ type: 'ready', value: !isReady })
  }

  function handleForceStart() {
    send({ type: 'force_start' })
  }

  function handleSetLobbyBoard(boardId: string) {
    send({ type: 'set_board', board_id: boardId })
  }

  function handleSetLobbyGameMode(mode: GameMode) {
    send({ type: 'set_mode', game_mode: mode })
  }

  function handleTogglePause() {
    const next = !useGameStore.getState().gamePaused
    const msg: ClientMessage = { type: 'set_paused', value: next }
    send(msg)
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

  // ── Not connected: Name entry ──────────────────────────────────────────────
  if (!connected) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-4 p-8 bg-gray-900 text-white">
        <h1 className="text-4xl font-bold text-indigo-400">RoboRally</h1>
        <div className="flex flex-col gap-2 w-full max-w-xs">
          <input
            className="bg-gray-800 border border-gray-600 rounded px-3 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500"
            placeholder="Your name"
            value={playerName}
            onChange={e => setPlayerName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleConnect()}
            autoFocus
          />
          <button
            className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded px-4 py-2 disabled:opacity-40 disabled:cursor-not-allowed"
            disabled={!playerName.trim()}
            onClick={handleConnect}
          >
            Browse Rooms →
          </button>
        </div>
      </div>
    )
  }

  // ── Connected, not in a room: Room browser ─────────────────────────────────
  if (!roomId) {
    const joinableRooms = rooms.filter(r => !r.in_progress)
    return (
      <div className="flex flex-col items-center min-h-screen gap-6 p-8 bg-gray-900 text-white">
        <h1 className="text-4xl font-bold text-indigo-400">RoboRally</h1>
        <p className="text-gray-400 text-sm -mt-3">
          Playing as <span className="text-white font-medium">{playerName}</span>
        </p>

        {/* Room list */}
        <div className="w-full max-w-md">
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-2">Available Rooms</h2>
          {joinableRooms.length === 0 ? (
            <p className="text-gray-500 text-sm italic py-2">No open rooms — create one below.</p>
          ) : (
            <div className="flex flex-col gap-2">
              {joinableRooms.map(r => (
                <div key={r.room_id} className="flex items-center justify-between bg-gray-800 rounded px-4 py-3">
                  <div>
                    <span className="font-medium">{r.room_name}</span>
                    <span className="text-gray-400 text-sm ml-2">
                      {r.player_count}/{r.required_players} players
                    </span>
                    {r.board_name ? (
                      <span className="block text-gray-500 text-xs mt-0.5">Map: {r.board_name}</span>
                    ) : null}
                    <span className="block text-gray-500 text-xs mt-0.5">Mode: {gameModeLabel(r.game_mode ?? 'standard')}</span>
                  </div>
                  <button
                    className="bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded px-3 py-1"
                    onClick={() => handleJoinRoom(r.room_id)}
                  >
                    Join
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Create room form */}
        <div className="w-full max-w-md border border-gray-700 rounded p-4 flex flex-col gap-3">
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide">Create a Room</h2>
          <input
            className="bg-gray-800 border border-gray-600 rounded px-3 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500"
            placeholder="Room name"
            value={createRoomName}
            onChange={e => setCreateRoomName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleCreateRoom()}
          />
          <div className="flex items-center gap-3">
            <span className="text-gray-400 text-sm">Players needed:</span>
            {[1, 2, 3, 4].map(n => (
              <button
                key={n}
                className={`w-8 h-8 rounded font-semibold text-sm transition-colors ${
                  createRequired === n
                    ? 'bg-indigo-600 text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
                onClick={() => setCreateRequired(n)}
              >
                {n}
              </button>
            ))}
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-gray-400 text-sm">Game mode</span>
            <ModeSelector value={createGameMode} onChange={setCreateGameMode} />
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-gray-400 text-sm">Factory map</span>
            <select
              className="bg-gray-800 border border-gray-600 rounded px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
              value={createBoardId}
              onChange={e => setCreateBoardId(e.target.value)}
            >
              {availableBoards.length === 0 ? (
                <option value="dizzy_highway">Dizzy Highway</option>
              ) : (
                availableBoards.map(b => (
                  <option key={b.id} value={b.id}>
                    {b.name}
                  </option>
                ))
              )}
            </select>
          </div>
          <button
            className="bg-green-700 hover:bg-green-600 text-white font-semibold rounded px-4 py-2 disabled:opacity-40 disabled:cursor-not-allowed"
            disabled={!createRoomName.trim()}
            onClick={handleCreateRoom}
          >
            Create Room
          </button>
        </div>
      </div>
    )
  }

  // ── In room, waiting to start: Waiting room ────────────────────────────────
  if (phase === 'lobby') {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-6 p-8 bg-gray-900 text-white">
        <h1 className="text-4xl font-bold text-indigo-400">RoboRally</h1>

        <div className="text-center">
          <p className="text-xl font-bold">{roomName || roomId}</p>
          <p className="text-gray-500 text-xs mt-0.5">Room ID: {roomId}</p>
        </div>

        <div className="w-full max-w-sm">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-gray-400 uppercase tracking-wide font-semibold">Game mode</span>
            {isHost ? (
              <ModeSelector value={lobbyGameMode} onChange={handleSetLobbyGameMode} />
            ) : (
              <p className="text-gray-200 rounded border border-gray-700 bg-gray-800/60 px-3 py-2">
                {gameModeLabel(lobbyGameMode)}
              </p>
            )}
          </label>
        </div>

        <div className="w-full max-w-sm">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-gray-400 uppercase tracking-wide font-semibold">Factory map</span>
            {isHost ? (
              <select
                className="bg-gray-800 border border-gray-600 rounded px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                value={lobbyBoardId}
                onChange={e => handleSetLobbyBoard(e.target.value)}
              >
                {(availableBoards.length ? availableBoards : [{ id: 'dizzy_highway', name: 'Dizzy Highway' }]).map(b => (
                  <option key={b.id} value={b.id}>
                    {b.name}
                  </option>
                ))}
              </select>
            ) : (
              <p className="text-gray-200 rounded border border-gray-700 bg-gray-800/60 px-3 py-2">
                {lobbyBoardName || lobbyBoardId}
              </p>
            )}
          </label>
        </div>

        {/* Roster */}
        <div className="w-full max-w-sm">
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-2">
            Players ({lobbyPlayers.length}/{requiredPlayers})
          </h2>
          <div className="flex flex-col gap-2">
            {lobbyPlayers.map(p => (
              <div key={p.player_id} className="flex items-center gap-3 bg-gray-800 rounded px-4 py-2">
                <span className="flex-1 font-medium">
                  {p.player_id}
                  {p.player_id === playerId && (
                    <span className="text-gray-500 text-xs ml-1">(you)</span>
                  )}
                </span>
                {p.is_host && (
                  <span className="text-yellow-400 text-xs font-semibold">HOST</span>
                )}
                {p.is_ready
                  ? <span className="text-green-400 text-xs font-semibold">✓ Ready</span>
                  : <span className="text-gray-500 text-xs">Waiting…</span>
                }
              </div>
            ))}
            {lobbyPlayers.length === 0 && (
              <p className="text-gray-500 text-sm italic py-2">Waiting for players…</p>
            )}
          </div>
        </div>

        <p className="text-gray-400 text-sm">
          {readyCount} / {lobbyPlayers.length} ready — need {requiredPlayers} to start
        </p>

        {/* Actions */}
        <div className="flex flex-col gap-2 w-full max-w-xs">
          <button
            className={`font-semibold rounded px-4 py-2 transition-colors ${
              isReady
                ? 'bg-gray-600 hover:bg-gray-500 text-white'
                : 'bg-green-700 hover:bg-green-600 text-white'
            }`}
            onClick={handleToggleReady}
          >
            {isReady ? 'Not Ready' : 'Ready ✓'}
          </button>
          {isHost && (
            <button
              className="bg-yellow-700 hover:bg-yellow-600 text-white font-semibold rounded px-4 py-2 disabled:opacity-40 disabled:cursor-not-allowed"
              onClick={handleForceStart}
              title="Start immediately with current players"
            >
              Force Start
            </button>
          )}
        </div>
      </div>
    )
  }

  // ── In-game ────────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col h-screen bg-gray-900 text-white">
      <header className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700 flex-shrink-0 gap-2">
        <span className="font-bold text-indigo-400">RoboRally</span>
        <span className="text-sm text-gray-400 capitalize text-center flex-1 min-w-0">
          {gamePaused && <span className="text-amber-400 mr-2">Paused</span>}
          {phase === 'programming' ? 'Programming' : phase === 'activation' ? 'Activation' : phase}
        </span>
        <div className="flex items-center gap-2 flex-shrink-0">
          {isHost && (phase === 'programming' || phase === 'activation') && (
            <button
              type="button"
              className="text-sm font-semibold rounded px-3 py-1 bg-amber-800 hover:bg-amber-700 text-white"
              onClick={handleTogglePause}
            >
              {gamePaused ? 'Resume' : 'Pause'}
            </button>
          )}
          <span className="text-sm text-gray-500 truncate max-w-[10rem]">{roomName || roomId}</span>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        <div className="relative flex-1">
          <Scene />
          <ActivationPlaybackHud />
        </div>
        <PlayerPanel />
      </div>

      {phase === 'programming' && <ProgrammingPanel />}
      <RoundResultOverlay />
    </div>
  )
}
