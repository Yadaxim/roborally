import { useEffect, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import { useSpring } from '@react-spring/three'
import { Color, Group, MeshStandardMaterial } from 'three'
import type { Robot } from '../../types/game'
import { useGameStore } from '../../store/gameStore'
import { DAMAGE_FLASH_DURATION_MS } from '../../utils/damageFlash'
import { DESTROY_SINK_MS } from '../../utils/destroySink'
import { RESPAWN_POP_MS } from '../../utils/respawnPop'

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
  const lastPopCleared = useRef<number | null>(null)

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
    const g = groupRef.current
    g.position.x = px.get()
    g.position.z = pz.get()
    g.rotation.y = ry.get()

    const st = useGameStore.getState()
    const now = Date.now()
    const sinkUntil = st.destroySinkUntil[robot.id] ?? 0
    const popStart = st.respawnPopStart[robot.id]

    let sinkY = 0
    let sinkS = 1
    if (sinkUntil > now && robot.is_alive) {
      const frac = Math.min(1, Math.max(0, (sinkUntil - now) / DESTROY_SINK_MS))
      sinkY = -1.25 * (1 - frac)
      sinkS = 0.08 + 0.92 * frac
    }

    let popY = 0
    let popS = 1
    if (robot.is_alive && popStart !== undefined) {
      const t = Math.min(1, Math.max(0, (now - popStart) / RESPAWN_POP_MS))
      const ease = 1 - (1 - t) ** 3
      popY = -0.38 * (1 - ease)
      popS = 0.12 + 0.88 * ease
      if (t >= 1 && lastPopCleared.current !== popStart) {
        lastPopCleared.current = popStart
        st.clearRespawnPop(robot.id)
      }
    }

    g.position.y = 0.15 + sinkY + popY
    g.scale.setScalar(sinkS * popS)

    const until = st.damageFlashUntil[robot.id] ?? 0
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
