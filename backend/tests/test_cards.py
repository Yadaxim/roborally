from collections import Counter

import pytest

from game.cards import Card, CardType, build_deck, deal


class TestDeck:
    def test_deck_has_84_cards(self):
        assert len(build_deck()) == 84

    def test_deck_card_type_counts(self):
        counts = Counter(c.type for c in build_deck())
        assert counts[CardType.MOVE_1] == 18
        assert counts[CardType.MOVE_2] == 12
        assert counts[CardType.MOVE_3] == 6
        assert counts[CardType.BACK_UP] == 6
        assert counts[CardType.TURN_LEFT] == 18
        assert counts[CardType.TURN_RIGHT] == 18
        assert counts[CardType.U_TURN] == 6

    def test_all_priorities_are_unique(self):
        priorities = [c.priority for c in build_deck()]
        assert len(priorities) == len(set(priorities))

    def test_move3_has_higher_priority_than_move1(self):
        deck = build_deck()
        min_move3 = min(c.priority for c in deck if c.type == CardType.MOVE_3)
        max_move1 = max(c.priority for c in deck if c.type == CardType.MOVE_1)
        assert min_move3 > max_move1

    def test_move2_priority_between_move1_and_move3(self):
        deck = build_deck()
        min_move2 = min(c.priority for c in deck if c.type == CardType.MOVE_2)
        max_move1 = max(c.priority for c in deck if c.type == CardType.MOVE_1)
        min_move3 = min(c.priority for c in deck if c.type == CardType.MOVE_3)
        assert max_move1 < min_move2
        assert min_move2 < min_move3

    def test_rotations_have_lower_priority_than_moves(self):
        deck = build_deck()
        rotation_types = {CardType.TURN_LEFT, CardType.TURN_RIGHT, CardType.U_TURN}
        max_rotation = max(c.priority for c in deck if c.type in rotation_types)
        min_move = min(
            c.priority for c in deck
            if c.type in {CardType.MOVE_1, CardType.MOVE_2, CardType.MOVE_3}
        )
        assert max_rotation < min_move

    def test_build_deck_returns_new_list_each_call(self):
        assert build_deck() is not build_deck()


class TestDeal:
    def test_deal_returns_9_cards_at_zero_damage(self):
        assert len(deal(build_deck(), damage=0)) == 9

    def test_deal_reduces_hand_size_by_damage(self):
        deck = build_deck()
        for damage in range(10):
            assert len(deal(deck, damage=damage)) == 9 - damage

    def test_deal_at_9_damage_returns_empty_hand(self):
        assert deal(build_deck(), damage=9) == []

    def test_dealt_cards_are_from_the_deck(self):
        deck = build_deck()
        hand = deal(deck, damage=0)
        assert all(c in deck for c in hand)

    def test_dealt_cards_have_no_duplicates(self):
        hand = deal(build_deck(), damage=0)
        assert len(hand) == len(set(hand))

    def test_deal_does_not_mutate_deck(self):
        deck = build_deck()
        original_len = len(deck)
        deal(deck, damage=0)
        assert len(deck) == original_len

    def test_deal_is_random(self):
        deck = build_deck()
        hands = [frozenset(deal(deck, damage=0)) for _ in range(5)]
        assert len(set(hands)) > 1
