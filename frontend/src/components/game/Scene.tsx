import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { useRef, useState } from 'react'
import { Vector3 } from 'three'
import { useGameStore } from '../../store/gameStore'
import Board3D from './Board3D'
import Robot3D from './Robot3D'
import LaserBeam3D from './LaserBeam3D'

const PLAYER_COLORS = ['#e63946', '#2a9d8f', '#e9c46a', '#f4a261']

/** Board middle tile for 12×12 grid at integer positions 0..11 */
const LOOK_AT = new Vector3(5.5, 0, 5.5)

/** Horizontal distance from board center in the XZ plane (orbit radius). */
const ORBIT_RADIUS = 9.2

function degreesToRad(d: number) {
  return (d * Math.PI) / 180
}

function CameraController({
  isometric,
  orbitDeg,
  elevDeg,
}: {
  isometric: boolean
  orbitDeg: number
  elevDeg: number
}) {
  const { camera } = useThree()
  const targetRef = useRef(new Vector3(12, 12, 12))

  useFrame(() => {
    if (!isometric) {
      targetRef.current.set(5.5, 20, 5.5)
    } else {
      const orbit = degreesToRad(orbitDeg)
      const elev = degreesToRad(Math.min(85, Math.max(10, elevDeg)))
      const h = ORBIT_RADIUS * Math.tan(elev)
      targetRef.current.set(
        5.5 + ORBIT_RADIUS * Math.cos(orbit),
        h,
        5.5 + ORBIT_RADIUS * Math.sin(orbit),
      )
    }
    camera.position.lerp(targetRef.current, 0.06)
    camera.lookAt(LOOK_AT)
  })
  return null
}

export default function Scene() {
  const robots = useGameStore(s => s.robots)
  const laserBeamPath = useGameStore(s => s.laserBeamPath)
  const [isometric, setIsometric] = useState(true)
  /** Orbit angle (°) around Y through board center; 0 = +X direction */
  const [orbitDeg, setOrbitDeg] = useState(45)
  /** Elevation (°) above XZ plane toward camera */
  const [elevDeg, setElevDeg] = useState(52.5)

  return (
    <div className="relative w-full h-full">
      <Canvas orthographic camera={{ position: [12, 12, 12], zoom: 40, near: -100, far: 100 }}>
        <CameraController isometric={isometric} orbitDeg={orbitDeg} elevDeg={elevDeg} />
        <ambientLight intensity={0.5} />
        <directionalLight position={[8, 12, 8]} intensity={1} />
        <Board3D />
        {laserBeamPath && laserBeamPath.length >= 2 && (
          <LaserBeam3D path={laserBeamPath} />
        )}
        {robots.map((r, i) => (
          <Robot3D key={r.id} robot={r} color={PLAYER_COLORS[i % PLAYER_COLORS.length]} />
        ))}
      </Canvas>
      <button
        type="button"
        className="absolute top-2 right-2 bg-gray-800/80 hover:bg-gray-700 text-white text-xs rounded px-3 py-1 border border-gray-600"
        onClick={() => setIsometric(v => !v)}
      >
        {isometric ? 'Top-down' : 'Isometric'}
      </button>

      {isometric && (
        <div className="absolute bottom-2 left-2 max-w-[11rem] rounded-md border border-gray-600 bg-gray-900/85 px-2.5 py-2 text-[11px] text-gray-200 shadow-lg backdrop-blur-sm">
          <p className="mb-1.5 font-semibold uppercase tracking-wide text-gray-400">Isometric view</p>
          <label className="flex flex-col gap-0.5 mb-2">
            <span className="flex justify-between text-gray-400">
              <span>Rotation</span>
              <span className="tabular-nums text-gray-300">{Math.round(orbitDeg)}°</span>
            </span>
            <input
              type="range"
              min={0}
              max={360}
              step={1}
              value={orbitDeg}
              onChange={e => setOrbitDeg(Number(e.target.value))}
              className="w-full accent-indigo-500"
            />
          </label>
          <label className="flex flex-col gap-0.5">
            <span className="flex justify-between text-gray-400">
              <span>Elevation</span>
              <span className="tabular-nums text-gray-300">{elevDeg.toFixed(0)}°</span>
            </span>
            <input
              type="range"
              min={15}
              max={75}
              step={0.5}
              value={elevDeg}
              onChange={e => setElevDeg(Number(e.target.value))}
              className="w-full accent-indigo-500"
            />
          </label>
        </div>
      )}
    </div>
  )
}
