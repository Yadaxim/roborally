import type { RoomSummary } from '../types/game'

function randomBase36(len: number): string {
  let s = ''
  for (let i = 0; i < len; i++) {
    s += Math.floor(Math.random() * 36).toString(36)
  }
  return s
}

function pick<T>(xs: readonly T[]): T {
  return xs[Math.floor(Math.random() * xs.length)]!
}

/** First half of compound handle (e.g. Rust…, Gear…). */
const HANDLE_FIRST = [
  'Rust',
  'Gear',
  'Spark',
  'Bolt',
  'Oil',
  'Chip',
  'Ram',
  'Servo',
  'Gyro',
  'Torque',
  'Weld',
  'Nut',
  'Battle',
  'Loose',
  'Steam',
  'Smoke',
  'Coal',
  'Steel',
  'Iron',
  'Brass',
  'Copper',
  'Flint',
  'Arc',
  'Volt',
  'Watt',
  'Laser',
  'Plasma',
  'Ion',
  'Nano',
  'Turbo',
  'Hydro',
  'Cryo',
  'Pyro',
  'Sonic',
  'Echo',
  'Void',
  'Chaos',
  'Doom',
  'Grim',
  'Wild',
  'Mad',
  'Hot',
  'Cold',
  'Junk',
  'Scrap',
  'Slag',
  'Grit',
  'Grime',
  'Frost',
  'Blaze',
] as const

/** Second half of compound handle (e.g. …Bucket, …Screw). */
const HANDLE_SECOND = [
  'Bucket',
  'Screw',
  'Plug',
  'Grinder',
  'Eater',
  'Face',
  'Lord',
  'Damage',
  'Rage',
  'Fiend',
  'Slayer',
  'Grump',
  'Maul',
  'Punk',
  'Witch',
  'Riveter',
  'Walker',
  'Tank',
  'Mech',
  'Clanker',
  'Bot',
  'Drive',
  'Core',
  'Head',
  'Jaw',
  'Fang',
  'Claw',
  'Hammer',
  'Anvil',
  'Forge',
  'Furnace',
  'Crucible',
  'Piston',
  'Valve',
  'Gasket',
  'Bearing',
  'Sprocket',
  'Chain',
  'Cog',
  'Wheel',
  'Axle',
  'Gremlin',
  'Goblin',
  'Beast',
  'Monster',
  'Titan',
  'Kraken',
  'Wreck',
  'Muncher',
  'Stomper',
] as const

/** Prepended for ~25% of names: “Captain-RustBucket”. */
const SILLY_PREFIXES = [
  'Sir',
  'Lady',
  'Captain',
  'Doctor',
  'Professor',
  'Cadet',
  'Baron',
  'Dame',
  'Ensign',
  'Commodore',
] as const

function randomCompoundHandle(): string {
  return `${pick(HANDLE_FIRST)}${pick(HANDLE_SECOND)}`
}

/** Quirky robot-arena display: random first+second compound; 25% get a silly title prefix. */
export function proposePlayerName(): string {
  const handle = randomCompoundHandle()
  if (Math.random() < 0.25) {
    return `${pick(SILLY_PREFIXES)}${handle}`
  }
  return handle
}

/** Suggest a room title not already used in the lobby list (compares case-insensitively). */
export function proposeRoomName(rooms: RoomSummary[]): string {
  const taken = new Set(rooms.map(r => r.room_name.toLowerCase()))
  const bases = ['My Game', 'Battle Room', 'Dizzy Duel', 'Robo Lounge']
  for (const base of bases) {
    if (!taken.has(base.toLowerCase())) return base
  }
  for (let n = 2; n < 10_000; n++) {
    const label = `My Game ${n}`
    if (!taken.has(label.toLowerCase())) return label
  }
  return `Game ${randomBase36(6)}`
}
