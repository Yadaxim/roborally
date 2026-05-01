export interface TileData {
  x: number
  y: number
  type: string
  direction?: string
  speed?: number
  rotation?: string
  checkpoint_num?: number
  laser_count?: number
  active_registers?: number[]
  walls: string[]
}

export const DIZZY_HIGHWAY: {
  name: string
  width: number
  height: number
  start_positions: [number, number][]
  checkpoints: [number, number][]
  tiles: TileData[]
} = {
  name: 'Dizzy Highway',
  width: 12,
  height: 12,
  start_positions: [[1, 11], [3, 11], [7, 11], [9, 11]],
  checkpoints: [[9, 9], [5, 5], [2, 2]],
  tiles: [
    { x: 9, y: 9, type: 'checkpoint', checkpoint_num: 1, walls: [] },
    { x: 5, y: 5, type: 'checkpoint', checkpoint_num: 2, walls: [] },
    { x: 2, y: 2, type: 'checkpoint', checkpoint_num: 3, walls: [] },
    { x: 1, y: 10, type: 'repair', walls: [] },
    { x: 4, y: 8, type: 'pit', walls: [] },
    { x: 7, y: 8, type: 'pit', walls: [] },
    { x: 1, y: 5, type: 'pit', walls: [] },
    { x: 10, y: 5, type: 'pit', walls: [] },
    { x: 6, y: 3, type: 'pit', walls: [] },
    { x: 2, y: 9, type: 'conveyor', direction: 'north', speed: 1, walls: [] },
    { x: 2, y: 8, type: 'conveyor', direction: 'north', speed: 1, walls: [] },
    { x: 2, y: 7, type: 'conveyor', direction: 'north', speed: 1, walls: [] },
    { x: 2, y: 6, type: 'conveyor', direction: 'north', speed: 1, walls: [] },
    { x: 8, y: 6, type: 'conveyor', direction: 'south', speed: 1, walls: [] },
    { x: 8, y: 7, type: 'conveyor', direction: 'south', speed: 1, walls: [] },
    { x: 8, y: 8, type: 'conveyor', direction: 'south', speed: 1, walls: [] },
    { x: 5, y: 10, type: 'conveyor', direction: 'north', speed: 2, walls: [] },
    { x: 5, y: 9,  type: 'conveyor', direction: 'north', speed: 2, walls: [] },
    { x: 5, y: 8,  type: 'conveyor', direction: 'north', speed: 2, walls: [] },
    { x: 5, y: 7,  type: 'conveyor', direction: 'north', speed: 2, walls: [] },
    { x: 5, y: 6,  type: 'conveyor', direction: 'north', speed: 2, walls: [] },
    { x: 3, y: 4, type: 'gear', rotation: 'clockwise',         walls: [] },
    { x: 8, y: 4, type: 'gear', rotation: 'counter-clockwise', walls: [] },
    { x: 0,  y: 6, type: 'laser_emitter', direction: 'east', laser_count: 1, walls: ['west'] },
    { x: 11, y: 3, type: 'laser_emitter', direction: 'west', laser_count: 1, walls: ['east'] },
    { x: 0,  y: 9, type: 'pusher', direction: 'east', active_registers: [1, 3], walls: ['west'] },
  ],
}
