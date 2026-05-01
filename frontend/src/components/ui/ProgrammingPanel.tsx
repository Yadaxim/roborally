import { DndContext, DragOverlay, useDraggable, useDroppable } from '@dnd-kit/core'
import type { DragEndEvent, DragStartEvent } from '@dnd-kit/core'
import { useEffect, useState } from 'react'
import { useGameStore } from '../../store/gameStore'
import { send } from '../../ws/client'
import CardComponent from './CardComponent'
import type { Card } from '../../types/game'

const TIMEOUT = 30  // must match backend PROGRAMMING_TIMEOUT

function useCountdown(dealTime: number | null): number {
  const [remaining, setRemaining] = useState(TIMEOUT)
  useEffect(() => {
    if (dealTime === null) { setRemaining(TIMEOUT); return }
    const tick = () => setRemaining(Math.max(0, Math.ceil(TIMEOUT - (Date.now() - dealTime) / 1000)))
    tick()
    const id = setInterval(tick, 500)
    return () => clearInterval(id)
  }, [dealTime])
  return remaining
}

function DraggableCard({ card, isUsed }: { card: Card; isUsed: boolean }) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `card-${card.priority}`,
    data: { card },
    disabled: isUsed,
  })

  function handleClick() {
    if (isUsed || isDragging) return
    const store = useGameStore.getState()
    const slot = store.registers.findIndex(r => r === null)
    if (slot !== -1) store.setRegister(slot, card)
  }

  return (
    <div
      ref={setNodeRef}
      className={isDragging ? 'opacity-30' : ''}
      {...listeners}
      {...attributes}
    >
      <CardComponent card={card} dimmed={isUsed} onClick={handleClick} />
    </div>
  )
}

function DroppableSlot({ index, card }: { index: number; card: Card | null }) {
  const { setNodeRef, isOver } = useDroppable({ id: `register-${index}` })

  function handleRemove() {
    useGameStore.getState().setRegister(index, null)
  }

  return (
    <div
      ref={setNodeRef}
      className={[
        'w-14 h-20 rounded border-2 border-dashed flex items-center justify-center transition-colors',
        isOver ? 'border-green-400 bg-green-900/20' : 'border-gray-600',
      ].join(' ')}
    >
      {card
        ? <CardComponent card={card} onClick={handleRemove} />
        : <span className="text-xs text-gray-500">{index + 1}</span>
      }
    </div>
  )
}

export default function ProgrammingPanel() {
  const hand = useGameStore(s => s.hand)
  const registers = useGameStore(s => s.registers)
  const dealTime = useGameStore(s => s.dealTime)
  const remaining = useCountdown(dealTime)
  const [activeCard, setActiveCard] = useState<Card | null>(null)

  const usedPriorities = new Set(registers.filter(Boolean).map(c => c!.priority))
  const filled = registers.filter(Boolean).length

  function handleDragStart(event: DragStartEvent) {
    const data = event.active.data.current
    setActiveCard(data ? (data['card'] as Card) : null)
  }

  function handleDragEnd(event: DragEndEvent) {
    setActiveCard(null)
    const { active, over } = event
    if (!over) return
    const overId = over.id.toString()
    if (!overId.startsWith('register-')) return
    const slotIndex = parseInt(overId.split('-')[1])
    const data = active.data.current
    if (data) useGameStore.getState().setRegister(slotIndex, data['card'] as Card)
  }

  function handleConfirm() {
    const cards = registers.filter(Boolean) as Card[]
    if (cards.length === 5) send({ type: 'submit_registers', cards })
  }

  return (
    <div className="bg-gray-800 border-t border-gray-700 p-3 flex flex-col gap-2">
      <DndContext onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
        {/* Registers row */}
        <div className="flex gap-2 items-end">
          {registers.map((c, i) => (
            <DroppableSlot key={i} index={i} card={c} />
          ))}
          <div className="ml-auto flex flex-col items-end gap-1.5">
            <div className="flex items-center gap-2">
              <span className={`text-sm font-mono tabular-nums ${remaining < 10 ? 'text-red-400' : 'text-gray-400'}`}>
                {remaining}s
              </span>
              <button
                className="bg-green-700 hover:bg-green-600 text-white rounded px-4 py-2 font-semibold disabled:opacity-40 disabled:cursor-not-allowed"
                disabled={filled !== 5}
                onClick={handleConfirm}
              >
                Confirm
              </button>
            </div>
            {/* Timer bar */}
            <div className="w-full h-1 bg-gray-600 rounded overflow-hidden">
              <div
                className="h-1 rounded transition-all duration-500"
                style={{
                  width: `${(remaining / TIMEOUT) * 100}%`,
                  backgroundColor: remaining < 10 ? '#f87171' : '#818cf8',
                }}
              />
            </div>
          </div>
        </div>

        {/* Hand row */}
        <div className="flex flex-wrap gap-2">
          {hand.map(c => (
            <DraggableCard key={c.priority} card={c} isUsed={usedPriorities.has(c.priority)} />
          ))}
        </div>

        <DragOverlay dropAnimation={null}>
          {activeCard ? <CardComponent card={activeCard} /> : null}
        </DragOverlay>
      </DndContext>
    </div>
  )
}
