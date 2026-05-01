import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import { useSpring } from '@react-spring/three'
import { Group } from 'three'
import type { Robot } from '../../types/game'

const FACING_ANGLE: Record<string, number> = {
  north: 0,
  east:  -Math.PI / 2,
  south:  Math.PI,
  west:   Math.PI / 2,
}

interface Props {
  robot: Robot
  color: string
}

export default function Robot3D({ robot, color }: Props) {
  const groupRef = useRef<Group>(null)

  const { px, pz, ry } = useSpring({
    px: robot.x,
    pz: robot.y,
    ry: FACING_ANGLE[robot.facing] ?? 0,
    config: { mass: 1, tension: 170, friction: 26 },
  })

  useFrame(() => {
    if (!groupRef.current) return
    groupRef.current.position.x = px.get()
    groupRef.current.position.z = pz.get()
    groupRef.current.rotation.y = ry.get()
  })

  if (!robot.is_alive) return null

  return (
    <group ref={groupRef} position={[robot.x, 0.15, robot.y]}>
      {/* Body */}
      <mesh>
        <cylinderGeometry args={[0.25, 0.3, 0.2, 12]} />
        <meshStandardMaterial color={color} />
      </mesh>
      {/* Head */}
      <mesh position={[0, 0.2, 0]}>
        <boxGeometry args={[0.2, 0.15, 0.2]} />
        <meshStandardMaterial color={color} />
      </mesh>
      {/* Nose — white dot facing forward (north = -z) */}
      <mesh position={[0, 0.1, -0.3]}>
        <sphereGeometry args={[0.07, 8, 8]} />
        <meshStandardMaterial color="white" />
      </mesh>
    </group>
  )
}
