import { create } from 'zustand'
import type { Card, Phase, Robot, ActivationEvent, PendingRegister, RoomSummary, LobbyPlayer, BoardData, GameMode } from '../types/game'
import { nextDamageFlashUntil, pruneExpiredFlashes } from '../utils/damageFlash'
import { nextDestroySinkUntil, pruneExpiredDestroySinks } from '../utils/destroySink'
import { mergeRespawnPopStarts } from '../utils/respawnPop'
import { asGameMode } from '../utils/gameModes'

/** Must match backend `PROGRAMMING_TIMEOUT` (seconds). */
export const PROGRAMMING_TIMEOUT_SEC = 30

interface GameState {
  // Connection
  connected: boolean
  playerId: string | null
  roomId: string | null

  // Lobby
  rooms: RoomSummary[]
  lobbyPlayers: LobbyPlayer[]
  isHost: boolean
  roomName: string
  requiredPlayers: number
  /** Selected map in lobby (host can change before start). */
  lobbyBoardId: string
  lobbyBoardName: string
  /** Game mode for this room (host can change in lobby); engine is standard race until modes are implemented. */
  lobbyGameMode: GameMode
  /** Authoritative board from server once a match begins. */
  activeBoard: BoardData | null

  // Game
  phase: Phase
  robots: Robot[]
  hand: Card[]
  registers: (Card | null)[]
  lockedCards: Record<number, Card>
  lastEvents: ActivationEvent[]
  roundEvents: ActivationEvent[]
  showRoundResult: boolean
  winner: string | null
  dealTime: number | null
  gamePaused: boolean
  programmingSecondsRemaining: number | null

  // Animation queue
  pendingRegisters: PendingRegister[]
  /** During activation animation: register card + current rules sub-step */
  playbackHighlight: {
    registerNum: number
    card: Card | null
    substepId: string
    substepIndex: number
    substepTotal: number
  } | null
  /** Captured when activation begins — HUD uses this so cards stay visible if live `registers` changes */
  activationProgramCards: (Card | null)[] | null
  /** Polyline in board (x,y) space for a short laser flash during activation playback. */
  laserBeamPath: [number, number][] | null
  /** Per-robot wall-clock deadline (ms) for red damage hit tint during activation playback. */
  damageFlashUntil: Record<string, number>
  /** Per-robot sink-into-floor animation before mesh hides on destroy. */
  destroySinkUntil: Record<string, number>
  /** When a robot revives, wall-clock start (ms) for scale-up pop animation. */
  respawnPopStart: Record<string, number>

  // Actions
  setConnected: (v: boolean) => void
  setJoined: (
    playerId: string,
    roomId: string,
    roomName: string,
    isHost: boolean,
    requiredPlayers: number,
    lobbyBoardId?: string,
    lobbyBoardName?: string,
    lobbyGameMode?: string,
  ) => void
  setRooms: (rooms: RoomSummary[]) => void
  setLobbyPlayers: (players: LobbyPlayer[]) => void
  updateLobbyPlayerReady: (playerId: string, isReady: boolean) => void
  setLobbyBoard: (boardId: string, boardName: string) => void
  setLobbyGameMode: (mode: GameMode) => void
  setActiveBoard: (board: BoardData | null) => void
  setPhase: (phase: Phase) => void
  setRobots: (robots: Robot[]) => void
  updateRobot: (id: string, updates: Partial<Robot>) => void
  setHand: (hand: Card[]) => void
  setDeal: (hand: Card[], lockedCards: Record<number, Card>, programmingSecondsRemaining?: number | null) => void
  setRegister: (slot: number, card: Card | null) => void
  /** Replace all five registers at once (e.g. sync UI with server default program). */
  setRegistersFromProgram: (cards: Card[]) => void
  /** Server starts the 30s deadline after the first player submits (rules). */
  setProgrammingTimer: (programmingSecondsRemaining: number) => void
  clearRegisters: () => void
  setLastEvents: (events: ActivationEvent[]) => void
  appendRoundEvents: (events: ActivationEvent[]) => void
  setShowRoundResult: (show: boolean) => void
  setWinner: (winner: string | null) => void
  applyStateSync: (
    phase: Phase,
    robots: Robot[],
    hand: Card[],
    lockedCards: Record<number, Card>,
    paused?: boolean,
    programmingSecondsRemaining?: number | null,
    board?: BoardData | null,
  ) => void
  setGamePaused: (paused: boolean, programmingSecondsRemaining?: number | null) => void
  enqueueRegister: (msg: PendingRegister) => void
  dequeueRegister: () => PendingRegister | null
  setPlaybackHighlight: (
    v: {
      registerNum: number
      card: Card | null
      substepId: string
      substepIndex: number
      substepTotal: number
    } | null,
  ) => void
  setActivationProgramCards: (cards: (Card | null)[] | null) => void
  setLaserBeamPath: (path: [number, number][] | null) => void
  pulseDamageFlash: (robotId: string) => void
  beginDestroySink: (robotId: string) => void
  clearDestroySink: (robotId: string) => void
  clearRespawnPop: (robotId: string) => void
  reset: () => void
}

function buildRegistersFromLocked(lockedCards: Record<number, Card>): (Card | null)[] {
  const registers: (Card | null)[] = [null, null, null, null, null]
  for (const [regNum, card] of Object.entries(lockedCards)) {
    registers[Number(regNum) - 1] = card
  }
  return registers
}

const INITIAL: Pick<
  GameState,
  | 'connected' | 'playerId' | 'roomId'
  | 'rooms' | 'lobbyPlayers' | 'isHost' | 'roomName' | 'requiredPlayers' | 'lobbyBoardId' | 'lobbyBoardName' | 'lobbyGameMode' | 'activeBoard'
  | 'phase' | 'robots' | 'hand' | 'registers' | 'lockedCards'
  | 'lastEvents' | 'roundEvents' | 'showRoundResult' | 'winner' | 'dealTime'
  | 'gamePaused' | 'programmingSecondsRemaining' | 'pendingRegisters' | 'playbackHighlight'
  | 'activationProgramCards' | 'laserBeamPath' | 'damageFlashUntil' | 'destroySinkUntil' | 'respawnPopStart'
> = {
  connected: false,
  playerId: null,
  roomId: null,
  rooms: [],
  lobbyPlayers: [],
  isHost: false,
  roomName: '',
  requiredPlayers: 2,
  lobbyBoardId: 'dizzy_highway',
  lobbyBoardName: '',
  lobbyGameMode: 'standard',
  activeBoard: null,
  phase: 'lobby',
  robots: [],
  hand: [],
  registers: [null, null, null, null, null],
  lockedCards: {},
  lastEvents: [],
  roundEvents: [],
  showRoundResult: false,
  winner: null,
  dealTime: null,
  gamePaused: false,
  programmingSecondsRemaining: null,
  pendingRegisters: [],
  playbackHighlight: null,
  activationProgramCards: null,
  laserBeamPath: null,
  damageFlashUntil: {},
  destroySinkUntil: {},
  respawnPopStart: {},
}

export const useGameStore = create<GameState>((set) => ({
  ...INITIAL,

  setConnected: (connected) => set({ connected }),
  setJoined: (playerId, roomId, roomName, isHost, requiredPlayers, lobbyBoardId, lobbyBoardName, lobbyGameMode) =>
    set({
      playerId,
      roomId,
      roomName,
      isHost,
      requiredPlayers,
      lobbyBoardId: lobbyBoardId ?? 'dizzy_highway',
      lobbyBoardName: lobbyBoardName ?? '',
      lobbyGameMode: asGameMode(lobbyGameMode),
    }),
  setLobbyBoard: (lobbyBoardId, lobbyBoardName) => set({ lobbyBoardId, lobbyBoardName }),
  setLobbyGameMode: (lobbyGameMode) => set({ lobbyGameMode }),
  setActiveBoard: (activeBoard) => set({ activeBoard }),
  setRooms: (rooms) => set({ rooms }),
  setLobbyPlayers: (lobbyPlayers) => set({ lobbyPlayers }),
  updateLobbyPlayerReady: (playerId, isReady) =>
    set((s) => ({
      lobbyPlayers: s.lobbyPlayers.map(p =>
        p.player_id === playerId ? { ...p, is_ready: isReady } : p
      ),
    })),
  setPhase: (phase) => set({ phase }),
  setRobots: (robots) =>
    set((s) => ({
      robots,
      respawnPopStart: mergeRespawnPopStarts(s.respawnPopStart, s.robots, robots, Date.now()),
    })),
  updateRobot: (id, updates) =>
    set((s) => ({ robots: s.robots.map(r => r.id === id ? { ...r, ...updates } : r) })),
  setHand: (hand) => set({ hand, dealTime: Date.now() }),
  setDeal: (hand, lockedCards, programmingSecondsRemaining) => {
    const rem = programmingSecondsRemaining ?? null
    const dealTime =
      rem != null
        ? Date.now() - (PROGRAMMING_TIMEOUT_SEC - rem) * 1000
        : null
    return set({
      hand,
      lockedCards,
      registers: buildRegistersFromLocked(lockedCards),
      dealTime,
      gamePaused: false,
      programmingSecondsRemaining: rem,
      roundEvents: [],
      showRoundResult: false,
      playbackHighlight: null,
      activationProgramCards: null,
      laserBeamPath: null,
      damageFlashUntil: {},
      destroySinkUntil: {},
      respawnPopStart: {},
    })
  },
  setRegister: (slot, card) =>
    set((s) => {
      const regNum = slot + 1
      if (regNum in s.lockedCards) return {}
      const registers = [...s.registers]
      registers[slot] = card
      return { registers }
    }),
  setRegistersFromProgram: (cards) =>
    set(() =>
      cards.length === 5 ? { registers: [...cards] as (Card | null)[] } : {},
    ),
  setProgrammingTimer: (programmingSecondsRemaining) =>
    set({
      programmingSecondsRemaining,
      dealTime: Date.now() - (PROGRAMMING_TIMEOUT_SEC - programmingSecondsRemaining) * 1000,
    }),
  clearRegisters: () =>
    set((s) => ({ registers: buildRegistersFromLocked(s.lockedCards) })),
  setLastEvents: (lastEvents) => set({ lastEvents }),
  appendRoundEvents: (events) =>
    set((s) => ({ roundEvents: [...s.roundEvents, ...events] })),
  setShowRoundResult: (showRoundResult) => set({ showRoundResult }),
  setWinner: (winner) => set({ winner }),
  applyStateSync: (phase, robots, hand, lockedCards, paused, programmingSecondsRemaining, board) =>
    set((s) => ({
      phase,
      robots,
      hand,
      lockedCards,
      respawnPopStart: mergeRespawnPopStarts(s.respawnPopStart, s.robots, robots, Date.now()),
      gamePaused: paused ?? false,
      programmingSecondsRemaining: programmingSecondsRemaining ?? null,
      ...(board != null ? { activeBoard: board } : {}),
      ...(phase === 'programming'
        ? programmingSecondsRemaining != null
          ? {
              dealTime: Date.now() - (PROGRAMMING_TIMEOUT_SEC - programmingSecondsRemaining) * 1000,
            }
          : { dealTime: null }
        : {}),
    })),
  setGamePaused: (paused, programmingSecondsRemaining) =>
    set(() => ({
      gamePaused: paused,
      programmingSecondsRemaining: programmingSecondsRemaining ?? null,
      ...(programmingSecondsRemaining != null && !paused
        ? { dealTime: Date.now() - (PROGRAMMING_TIMEOUT_SEC - programmingSecondsRemaining) * 1000 }
        : {}),
    })),
  enqueueRegister: (msg) => set((s) => ({ pendingRegisters: [...s.pendingRegisters, msg] })),
  dequeueRegister: () => {
    let result: PendingRegister | null = null
    useGameStore.setState((s) => {
      if (s.pendingRegisters.length === 0) return {}
      const [first, ...rest] = s.pendingRegisters
      result = first
      return { pendingRegisters: rest }
    })
    return result
  },
  setPlaybackHighlight: (playbackHighlight) => set({ playbackHighlight }),
  setActivationProgramCards: (activationProgramCards) => set({ activationProgramCards }),
  setLaserBeamPath: (laserBeamPath) => set({ laserBeamPath }),
  pulseDamageFlash: (robotId) =>
    set((s) => {
      const now = Date.now()
      const trimmed = pruneExpiredFlashes(s.damageFlashUntil, now)
      return { damageFlashUntil: nextDamageFlashUntil(trimmed, robotId, now) }
    }),
  beginDestroySink: (robotId) =>
    set((s) => {
      const now = Date.now()
      const trimmed = pruneExpiredDestroySinks(s.destroySinkUntil, now)
      return { destroySinkUntil: nextDestroySinkUntil(trimmed, robotId, now) }
    }),
  clearDestroySink: (robotId) =>
    set((s) => {
      const next = { ...s.destroySinkUntil }
      delete next[robotId]
      return { destroySinkUntil: next }
    }),
  clearRespawnPop: (robotId) =>
    set((s) => {
      const next = { ...s.respawnPopStart }
      delete next[robotId]
      return { respawnPopStart: next }
    }),
  reset: () => set(INITIAL),
}))
