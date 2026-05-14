import { useEffect, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import { useSpring } from '@react-spring/three'
import { Color, Group, MeshStandardMaterial } from 'three'
import type { Robot } from '../../types/game'
import { useGameStore } from '../../store/gameStore'
import { DAMAGE_FLASH_DURATION_MS } from '../../utils/damageFlash'

const FACING_ANGLE: Record<string, number> = {
  north: 0,
  east:  -Math.PI / 2,
  south:  Math.PI,
  west:   Math.PI / 2,
}

const FLASH_RED = new Color('#ff2222')

interface Props {
  robot: Robot
  color: string
}

export default function Robot3D({ robot, color }: Props) {
  const groupRef = useRef<Group>(null)
  const baseBody = useRef(new Color())
  const baseHead = useRef(new Color())
  const bodyMatRef = useRef<MeshStandardMaterial | null>(null)
  const headMatRef = useRef<MeshStandardMaterial | null>(null)

  useEffect(() => {
    baseBody.current.set(color)
    baseHead.current.set(color)
    const b = bodyMatRef.current
    const h = headMatRef.current
    if (b) {
      b.color.copy(baseBody.current)
      b.emissive.setRGB(0, 0, 0)
    }
    if (h) {
      h.color.copy(baseHead.current)
      h.emissive.setRGB(0, 0, 0)
    }
  }, [color])

  const { px, pz, ry } = useSpring({
    px: robot.x,
    pz: robot.y,
    ry: FACING_ANGLE[robot.facing] ?? 0,
    config: { mass: 1, tension: 80, friction: 26 },
  })

  useFrame(() => {
    if (!groupRef.current) return
    groupRef.current.position.x = px.get()
    groupRef.current.position.z = pz.get()
    groupRef.current.rotation.y = ry.get()

    const until = useGameStore.getState().damageFlashUntil[robot.id] ?? 0
    const now = Date.now()
    const u = until > now ? Math.min(1, (until - now) / DAMAGE_FLASH_DURATION_MS) : 0
    const b = bodyMatRef.current
    const h = headMatRef.current
    if (b) {
      b.color.copy(baseBody.current).lerp(FLASH_RED, u)
      b.emissive.setRGB(u * 0.55, 0, 0)
    }
    if (h) {
      h.color.copy(baseHead.current).lerp(FLASH_RED, u)
      h.emissive.setRGB(u * 0.45, 0, 0)
    }
  })

  if (!robot.is_alive) return null

  return (
    <group ref={groupRef} position={[robot.x, 0.15, robot.y]}>
      {/* Body */}
      <mesh>
        <cylinderGeometry args={[0.25, 0.3, 0.2, 12]} />
        <meshStandardMaterial ref={bodyMatRef} color={color} />
      </mesh>
      {/* Head */}
      <mesh position={[0, 0.2, 0]}>
        <boxGeometry args={[0.2, 0.15, 0.2]} />
        <meshStandardMaterial ref={headMatRef} color={color} />
      </mesh>
      {/* Nose — white dot facing forward (north = -z) */}
      <mesh position={[0, 0.1, -0.3]}>
        <sphereGeometry args={[0.07, 8, 8]} />
        <meshStandardMaterial color="white" />
      </mesh>
    </group>
  )
}
