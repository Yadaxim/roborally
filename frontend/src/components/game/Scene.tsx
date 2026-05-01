import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { useRef, useState } from 'react'
import { Vector3 } from 'three'
import { useGameStore } from '../../store/gameStore'
import Board3D from './Board3D'
import Robot3D from './Robot3D'

const PLAYER_COLORS = ['#e63946', '#2a9d8f', '#e9c46a', '#f4a261']

function CameraController({ isometric }: { isometric: boolean }) {
  const { camera } = useThree()
  const targetRef = useRef(new Vector3(12, 12, 12))
  // Update target synchronously — safe on refs, no re-render triggered
  targetRef.current.set(
    isometric ? 12 : 5.5,
    isometric ? 12 : 20,
    isometric ? 12 : 5.5,
  )
  useFrame(() => {
    camera.position.lerp(targetRef.current, 0.06)
    camera.lookAt(5.5, 0, 5.5)
  })
  return null
}

export default function Scene() {
  const robots = useGameStore(s => s.robots)
  const [isometric, setIsometric] = useState(true)

  return (
    <div className="relative w-full h-full">
      <Canvas orthographic camera={{ position: [12, 12, 12], zoom: 40, near: -100, far: 100 }}>
        <CameraController isometric={isometric} />
        <ambientLight intensity={0.5} />
        <directionalLight position={[8, 12, 8]} intensity={1} />
        <Board3D />
        {robots.map((r, i) => (
          <Robot3D key={r.id} robot={r} color={PLAYER_COLORS[i % PLAYER_COLORS.length]} />
        ))}
      </Canvas>
      <button
        className="absolute top-2 right-2 bg-gray-800/80 hover:bg-gray-700 text-white text-xs rounded px-3 py-1 border border-gray-600"
        onClick={() => setIsometric(v => !v)}
      >
        {isometric ? 'Top-down' : 'Isometric'}
      </button>
    </div>
  )
}
