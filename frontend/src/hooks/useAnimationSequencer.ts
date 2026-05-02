import { useEffect, useRef } from 'react'
import { useGameStore } from '../store/gameStore'

const STEP_MS = 500      // delay between each move/rotate event
const REGISTER_PAUSE_MS = 800  // pause after each register finishes

function delay(ms: number) {
  return new Promise<void>(resolve => setTimeout(resolve, ms))
}

export function useAnimationSequencer() {
  const playing = useRef(false)
  const pendingLength = useGameStore(s => s.pendingRegisters.length)

  useEffect(() => {
    if (!playing.current && pendingLength > 0) playNext()
  }, [pendingLength])

  async function playNext() {
    playing.current = true
    const store = useGameStore.getState()
    const msg = store.dequeueRegister()
    if (!msg) { playing.current = false; return }

    for (const ev of msg.events) {
      if (ev.type === 'move' && ev.to) {
        store.updateRobot(ev.robot_id, { x: ev.to[0], y: ev.to[1] })
        await delay(STEP_MS)
      } else if (ev.type === 'rotate' && ev.to_dir) {
        store.updateRobot(ev.robot_id, { facing: ev.to_dir })
        await delay(STEP_MS)
      } else if (ev.type === 'destroy') {
        store.updateRobot(ev.robot_id, { is_alive: false })
      }
      // damage / laser / checkpoint have no 3D visual yet — handled by final setRobots
    }

    // Snap to authoritative final state (covers conveyors, push panels, damage totals)
    store.setRobots(msg.robots)
    store.setLastEvents(msg.events)
    store.appendRoundEvents(msg.events)

    await delay(REGISTER_PAUSE_MS)

    playing.current = false
    if (useGameStore.getState().pendingRegisters.length > 0) playNext()
  }
}
