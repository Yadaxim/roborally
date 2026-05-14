import { useEffect, useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import {
  AdditiveBlending,
  BufferGeometry,
  Float32BufferAttribute,
  Line,
  LineBasicMaterial,
} from 'three'

interface Props {
  /** Board (x, y) cells along the beam; scene uses XZ as the factory floor. */
  path: [number, number][]
}

const BEAM_Y = 0.42
const FADE_MS = 280

/**
 * Red polyline flash for the lasers activation sub-step. Opacity eases out while mounted.
 */
export default function LaserBeam3D({ path }: Props) {
  const startRef = useRef(performance.now())

  const lineObj = useMemo(() => {
    const g = new BufferGeometry()
    const arr = new Float32Array(path.length * 3)
    for (let i = 0; i < path.length; i++) {
      const [x, y] = path[i]!
      arr[i * 3] = x
      arr[i * 3 + 1] = BEAM_Y
      arr[i * 3 + 2] = y
    }
    g.setAttribute('position', new Float32BufferAttribute(arr, 3))
    const mat = new LineBasicMaterial({
      color: 0xff3344,
      transparent: true,
      opacity: 1,
      depthWrite: false,
      blending: AdditiveBlending,
    })
    return new Line(g, mat)
  }, [path])

  useEffect(() => {
    startRef.current = performance.now()
    const mat = lineObj.material as LineBasicMaterial
    mat.opacity = 1
    return () => {
      lineObj.geometry.dispose()
      ;(lineObj.material as LineBasicMaterial).dispose()
    }
  }, [lineObj, path])

  useFrame(() => {
    const mat = lineObj.material as LineBasicMaterial
    const u = (performance.now() - startRef.current) / FADE_MS
    mat.opacity = Math.max(0, 1 - u * u)
  })

  if (path.length < 2) return null

  const key = path.map(p => `${p[0]},${p[1]}`).join('|')
  return <primitive object={lineObj} key={key} />
}
