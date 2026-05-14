import { DIZZY_HIGHWAY } from '../../data/dizzyHighway'
import type { BoardData, TileData } from '../../types/game'
import { useGameStore } from '../../store/gameStore'
import Tile3D from './Tile3D'

export default function Board3D() {
  const activeBoard = useGameStore(s => s.activeBoard)
  const board: BoardData = activeBoard ?? DIZZY_HIGHWAY
  const { width, height, tiles } = board
  const tileMap = new Map<string, TileData>()
  for (const t of tiles) tileMap.set(`${t.x},${t.y}`, t)

  return (
    <group>
      {Array.from({ length: height }, (_, y) =>
        Array.from({ length: width }, (_, x) => {
          const tile: TileData = tileMap.get(`${x},${y}`) ?? { x, y, type: 'floor', walls: [] }
          return <Tile3D key={`${x},${y}`} tile={tile} />
        })
      )}
    </group>
  )
}
