import type { TileData } from '../../data/dizzyHighway'

const TILE_COLORS: Record<string, string> = {
  floor:         '#4a4a4a',
  conveyor:      '#1a6b3a',
  gear:          '#6b2d8b',
  repair:        '#2d4a8b',
  checkpoint:    '#8b6000',
  laser_emitter: '#8b1a1a',
  pusher:        '#5a3a00',
}

// Rotation to lay a +y-pointing cone flat in each board direction.
// Board north = -z in 3D, so Rx(π/2) points cone toward -z, then Ry rotates further.
const DIR_ROT: Record<string, [number, number, number]> = {
  north: [Math.PI / 2, 0,            0],
  east:  [Math.PI / 2, -Math.PI / 2, 0],
  south: [Math.PI / 2, Math.PI,      0],
  west:  [Math.PI / 2, Math.PI / 2,  0],
}

const CP_COLORS = ['#ffcc00', '#00cc66', '#cc3333']

function WallSegment({ side, tx, ty }: { side: string; tx: number; ty: number }) {
  const pos: [number, number, number] =
    side === 'north' ? [tx, 0.15, ty - 0.475]
    : side === 'south' ? [tx, 0.15, ty + 0.475]
    : side === 'east'  ? [tx + 0.475, 0.15, ty]
    : [tx - 0.475, 0.15, ty]
  const size: [number, number, number] =
    side === 'north' || side === 'south' ? [0.9, 0.25, 0.05] : [0.05, 0.25, 0.9]
  return (
    <mesh position={pos}>
      <boxGeometry args={size} />
      <meshStandardMaterial color="#cc8844" />
    </mesh>
  )
}

function CheckpointDecor({ x, y, num }: { x: number; y: number; num: number }) {
  return (
    <group position={[x, 0, y]}>
      <mesh position={[0, 0.3, 0]}>
        <cylinderGeometry args={[0.03, 0.03, 0.5, 8]} />
        <meshStandardMaterial color="#cccccc" />
      </mesh>
      <mesh position={[0.12, 0.55, 0]}>
        <sphereGeometry args={[0.12, 10, 10]} />
        <meshStandardMaterial color={CP_COLORS[(num - 1) % CP_COLORS.length]} />
      </mesh>
    </group>
  )
}

function ConveyorArrow({ x, y, dir, speed }: { x: number; y: number; dir: string; speed: number }) {
  const rot = DIR_ROT[dir] ?? DIR_ROT['north']
  return (
    <mesh position={[x, 0.07, y]} rotation={rot}>
      <coneGeometry args={[0.22, 0.5, 4]} />
      <meshStandardMaterial color={speed === 2 ? '#88ccff' : '#88ffaa'} transparent opacity={0.9} />
    </mesh>
  )
}

function GearDecor({ x, y }: { x: number; y: number }) {
  return (
    <mesh position={[x, 0.06, y]}>
      <cylinderGeometry args={[0.35, 0.35, 0.02, 16]} />
      <meshStandardMaterial color="#222222" />
    </mesh>
  )
}

export default function Tile3D({ tile }: { tile: TileData }) {
  if (tile.type === 'pit') {
    return (
      <mesh position={[tile.x, -0.3, tile.y]}>
        <cylinderGeometry args={[0.42, 0.42, 0.5, 16]} />
        <meshStandardMaterial color="#080808" />
      </mesh>
    )
  }

  const color =
    tile.type === 'conveyor' && tile.speed === 2
      ? '#1a3a8b'
      : TILE_COLORS[tile.type] ?? '#4a4a4a'

  return (
    <group>
      <mesh position={[tile.x, 0, tile.y]}>
        <boxGeometry args={[0.95, 0.1, 0.95]} />
        <meshStandardMaterial color={color} />
      </mesh>
      {tile.walls.map(side => (
        <WallSegment key={side} side={side} tx={tile.x} ty={tile.y} />
      ))}
      {tile.type === 'checkpoint' && tile.checkpoint_num !== undefined && (
        <CheckpointDecor x={tile.x} y={tile.y} num={tile.checkpoint_num} />
      )}
      {tile.type === 'conveyor' && tile.direction !== undefined && (
        <ConveyorArrow x={tile.x} y={tile.y} dir={tile.direction} speed={tile.speed ?? 1} />
      )}
      {tile.type === 'gear' && (
        <GearDecor x={tile.x} y={tile.y} />
      )}
    </group>
  )
}
