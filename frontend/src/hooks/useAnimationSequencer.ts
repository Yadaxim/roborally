import { useEffect } from 'react'
import type { PendingRegister } from '../types/game'
import { useGameStore } from '../store/gameStore'
import { flushDeferredActivationMessages } from '../ws/client'

const MOVE_ROTATE_MS = 420
const OTHER_MS = 380
const REGISTER_PAUSE_MS = 650
const LASER_BEAM_FLASH_MS = 300

function delay(ms: number) {
  return new Promise<void>(resolve => setTimeout(resolve, ms))
}

async function waitUnpaused() {
  while (useGameStore.getState().gamePaused) {
    await delay(50)
  }
}

/** Only one drain runs at a time — avoids skipped batches (Strict Mode / overlapping playNext). */
let activeDrain: Promise<void> | null = null

/**
 * Single consumer for `pendingRegisters`: processes each activation **sub-step** in order.
 */
export function useAnimationSequencer() {
  useEffect(() => {
    const cancelled = { current: false }

    async function playOneSubstep(msg: PendingRegister) {
      const slot = msg.register_num - 1
      const s0 = useGameStore.getState()
      const program = s0.activationProgramCards ?? s0.registers
      s0.setPlaybackHighlight({
        registerNum: msg.register_num,
        card: program[slot] ?? null,
        substepId: msg.substep_id,
        substepIndex: msg.substep_index,
        substepTotal: msg.substep_total,
      })

      await waitUnpaused()

      for (const ev of msg.events) {
        if (cancelled.current) return
        await waitUnpaused()
        const store = useGameStore.getState()
        if (ev.type === 'move' && ev.to) {
          store.updateRobot(ev.robot_id, { x: ev.to[0], y: ev.to[1] })
          await delay(MOVE_ROTATE_MS)
        } else if (ev.type === 'rotate' && ev.to_dir) {
          store.updateRobot(ev.robot_id, { facing: ev.to_dir })
          await delay(MOVE_ROTATE_MS)
        } else if (ev.type === 'destroy') {
          store.updateRobot(ev.robot_id, { is_alive: false })
          await delay(OTHER_MS)
        } else if (ev.type === 'laser') {
          const lp = ev.laser_path
          if (lp && lp.length >= 2) {
            store.setLaserBeamPath(lp as [number, number][])
            await delay(LASER_BEAM_FLASH_MS)
            store.setLaserBeamPath(null)
          } else {
            await delay(OTHER_MS)
          }
        } else if (ev.type === 'checkpoint') {
          await delay(OTHER_MS)
        }
      }

      const s1 = useGameStore.getState()
      s1.setRobots(msg.robots)
      s1.setLastEvents(msg.events)
      s1.appendRoundEvents(msg.events)

      await waitUnpaused()
      if (msg.substep_index === msg.substep_total) {
        await delay(REGISTER_PAUSE_MS)
      }
    }

    async function drainLoop() {
      while (!cancelled.current && useGameStore.getState().pendingRegisters.length > 0) {
        const msg = useGameStore.getState().dequeueRegister()
        if (!msg) break
        await playOneSubstep(msg)
      }
      if (!cancelled.current) {
        useGameStore.getState().setPlaybackHighlight(null)
        flushDeferredActivationMessages()
      }
    }

    function kickDrain() {
      if (cancelled.current || activeDrain) return
      if (useGameStore.getState().pendingRegisters.length === 0) return
      activeDrain = drainLoop().finally(() => {
        activeDrain = null
        if (!cancelled.current && useGameStore.getState().pendingRegisters.length > 0) {
          kickDrain()
        }
      })
    }

    const unsub = useGameStore.subscribe(kickDrain)
    kickDrain()

    return () => {
      cancelled.current = true
      unsub()
    }
  }, [])
}
