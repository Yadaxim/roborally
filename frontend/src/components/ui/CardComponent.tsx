import type { Card, CardType } from '../../types/game'

const CARD_COLORS: Record<CardType, string> = {
  move_1:     'bg-blue-900  border-blue-600',
  move_2:     'bg-blue-900  border-blue-600',
  move_3:     'bg-blue-800  border-blue-500',
  back_up:    'bg-orange-900 border-orange-600',
  turn_left:  'bg-yellow-900 border-yellow-600',
  turn_right: 'bg-yellow-900 border-yellow-600',
  u_turn:     'bg-red-900   border-red-600',
}

const CARD_ICONS: Record<CardType, string> = {
  move_1:     '↑',
  move_2:     '↑↑',
  move_3:     '↑↑↑',
  back_up:    '↓',
  turn_left:  '↺',
  turn_right: '↻',
  u_turn:     '↩',
}

const CARD_LABELS: Record<CardType, string> = {
  move_1:     'Move 1',
  move_2:     'Move 2',
  move_3:     'Move 3',
  back_up:    'Back',
  turn_left:  'Left',
  turn_right: 'Right',
  u_turn:     'U-Turn',
}

interface CardProps {
  card: Card
  dimmed?: boolean
  onClick?: () => void
}

export default function CardComponent({ card, dimmed = false, onClick }: CardProps) {
  const colors = CARD_COLORS[card.type]
  const interactive = !!onClick && !dimmed
  return (
    <div
      className={[
        'w-14 h-20 rounded border-2 flex flex-col items-center justify-between p-1 select-none',
        colors,
        dimmed ? 'opacity-30' : interactive ? 'cursor-pointer hover:brightness-125' : '',
      ].join(' ')}
      onClick={interactive ? onClick : undefined}
    >
      <span className="text-xs text-gray-300 font-medium leading-none text-center">
        {CARD_LABELS[card.type]}
      </span>
      <span className="text-2xl leading-none">{CARD_ICONS[card.type]}</span>
      <span className="text-xs text-gray-400 font-mono leading-none">{card.priority}</span>
    </div>
  )
}
