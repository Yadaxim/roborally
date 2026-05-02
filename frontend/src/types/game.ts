export type CardType =
  | 'u_turn'
  | 'turn_left'
  | 'turn_right'
  | 'back_up'
  | 'move_1'
  | 'move_2'
  | 'move_3'

export interface Card {
  type: CardType
  priority: number
}

export type Direction = 'north' | 'south' | 'east' | 'west'
export type Phase = 'lobby' | 'programming' | 'activation' | 'game_over'

export interface Robot {
  id: string
  x: number
  y: number
  facing: Direction
  damage: number
  lives: number
  checkpoints_touched: number
  is_alive: boolean
  locked_registers: number[]
}

export interface ActivationEvent {
  type: 'move' | 'rotate' | 'damage' | 'destroy' | 'laser' | 'checkpoint'
  robot_id: string
  from_pos?: [number, number]
  to?: [number, number]
  from_dir?: Direction
  to_dir?: Direction
  amount?: number
  laser_path?: [number, number][]
  checkpoint_num?: number
}

export interface PendingRegister {
  register_num: number
  events: ActivationEvent[]
  robots: Robot[]
}

export interface RoomSummary {
  room_id: string
  room_name: string
  host_id: string
  player_count: number
  required_players: number
  in_progress: boolean
}

export interface LobbyPlayer {
  player_id: string
  is_host: boolean
  is_ready: boolean
}

// Server → Client messages
export type ServerMessage =
  | { type: 'room_list'; rooms: RoomSummary[] }
  | { type: 'joined'; player_id: string; room_id: string; room_name: string; is_host: boolean; required_players: number }
  | { type: 'roster_update'; players: LobbyPlayer[] }
  | { type: 'player_ready'; player_id: string; is_ready: boolean }
  | { type: 'game_started'; robots: Robot[] }
  | { type: 'deal_hand'; hand: Card[]; locked_cards: Record<number, Card> }
  | { type: 'phase_change'; phase: Phase }
  | { type: 'state_sync'; phase: Phase; robots: Robot[]; hand: Card[]; locked_cards: Record<number, Card> }
  | { type: 'register_events'; register_num: number; events: ActivationEvent[]; robots: Robot[] }
  | { type: 'game_over'; winner: string | null }
  | { type: 'error'; message: string }

// Client → Server messages
export type ClientMessage =
  | { type: 'join'; room_id: string; player_id: string }
  | { type: 'create_room'; player_name: string; room_name: string; required_players: number }
  | { type: 'join_room'; player_name: string; room_id: string }
  | { type: 'ready'; value: boolean }
  | { type: 'force_start' }
  | { type: 'start' }
  | { type: 'submit_registers'; cards: Card[] }
