import { useGameStore } from '../../store/gameStore'
import CardComponent from './CardComponent'
import { labelForSubstepId } from '../../utils/registerSubstepLabels'

/** Register card + rules sub-step while activation runs (matches board timing). */
export default function ActivationPlaybackHud() {
  const phase = useGameStore(s => s.phase)
  const playbackHighlight = useGameStore(s => s.playbackHighlight)

  if (phase !== 'activation' || !playbackHighlight) return null

  const { registerNum, card, substepId, substepIndex, substepTotal } = playbackHighlight
  const subLabel = labelForSubstepId(substepId)

  return (
    <div className="pointer-events-none absolute left-3 top-14 z-10 flex flex-col items-start gap-2 rounded-lg border border-indigo-500/40 bg-gray-950/90 px-3 py-2 shadow-lg backdrop-blur-sm max-w-[14rem]">
      <div className="text-[11px] font-semibold uppercase tracking-wide text-indigo-300">
        Register <span className="tabular-nums text-white">{registerNum}</span>
        <span className="font-normal text-gray-500"> / 5</span>
      </div>
      <div className="text-[10px] leading-snug text-gray-300">
        <span className="text-indigo-200 font-medium">{subLabel}</span>
        <span className="text-gray-500">
          {' '}
          ({substepIndex}/{substepTotal})
        </span>
      </div>
      {card
        ? (
            <div className="scale-110 origin-top-left">
              <CardComponent card={card} />
            </div>
          )
        : (
            <div className="flex h-20 w-14 items-center justify-center rounded border border-dashed border-gray-600 text-[10px] text-gray-500">
              —
            </div>
          )}
    </div>
  )
}
