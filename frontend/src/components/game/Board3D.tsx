import { DIZZY_HIGHWAY, type TileData } from '../../data/dizzyHighway'
import Tile3D from './Tile3D'

export default function Board3D() {
  const { width, height, tiles } = DIZZY_HIGHWAY
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
