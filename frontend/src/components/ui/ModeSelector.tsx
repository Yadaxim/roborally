import type { GameMode } from '../../types/game'
import { GAME_MODE_OPTIONS } from '../../utils/gameModes'

interface Props {
  value: GameMode
  onChange: (mode: GameMode) => void
  disabled?: boolean
  id?: string
}

export default function ModeSelector({ value, onChange, disabled, id }: Props) {
  return (
    <select
      id={id}
      disabled={disabled}
      className="bg-gray-800 border border-gray-600 rounded px-3 py-2 text-white focus:outline-none focus:border-indigo-500 disabled:opacity-60 disabled:cursor-not-allowed w-full"
      value={value}
      onChange={e => onChange(e.target.value as GameMode)}
    >
      {GAME_MODE_OPTIONS.map(o => (
        <option key={o.id} value={o.id}>
          {o.label}
        </option>
      ))}
    </select>
  )
}
