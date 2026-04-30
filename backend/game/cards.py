import random
from dataclasses import dataclass
from enum import Enum


class CardType(Enum):
    U_TURN = "u_turn"
    BACK_UP = "back_up"
    TURN_LEFT = "turn_left"
    TURN_RIGHT = "turn_right"
    MOVE_1 = "move_1"
    MOVE_2 = "move_2"
    MOVE_3 = "move_3"


@dataclass(frozen=True)
class Card:
    type: CardType
    priority: int

    def __repr__(self) -> str:
        return f"Card({self.type.value}, p={self.priority})"


# Priority ranges (higher = executes first within a register)
# U-Turn:     10–60    step 10  (6 cards)
# Back Up:    70–120   step 10  (6 cards)
# Turn Left:  140–480  step 20  (18 cards)
# Turn Right: 150–490  step 20  (18 cards)
# Move 1:     500–670  step 10  (18 cards)
# Move 2:     680–790  step 10  (12 cards)
# Move 3:     800–850  step 10  (6 cards)
_CARD_DEFINITIONS: list[tuple[CardType, list[int]]] = [
    (CardType.U_TURN,     list(range(10,  70,  10))),   # 6
    (CardType.BACK_UP,    list(range(70,  130, 10))),   # 6
    (CardType.TURN_LEFT,  list(range(140, 500, 20))),   # 18
    (CardType.TURN_RIGHT, list(range(150, 510, 20))),   # 18
    (CardType.MOVE_1,     list(range(500, 680, 10))),   # 18
    (CardType.MOVE_2,     list(range(680, 800, 10))),   # 12
    (CardType.MOVE_3,     list(range(800, 860, 10))),   # 6
]


def build_deck() -> list[Card]:
    return [
        Card(type=card_type, priority=p)
        for card_type, priorities in _CARD_DEFINITIONS
        for p in priorities
    ]


def deal(deck: list[Card], damage: int) -> list[Card]:
    hand_size = max(0, 9 - damage)
    shuffled = deck.copy()
    random.shuffle(shuffled)
    return shuffled[:hand_size]
