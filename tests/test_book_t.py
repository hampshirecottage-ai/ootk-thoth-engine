"""Book T piles, counting and pairing (ootk.book_t), worked by hand against the text."""
import json
from pathlib import Path

import pytest

from ootk import book_t

DECK = json.loads((Path(__file__).parent / "fixtures" / "reference_cards.json").read_text())["deck"]
BY_TITLE = {c["title"]: c for c in DECK}


def card(prefix):
    return next(c for t, c in BY_TITLE.items() if t.startswith(prefix))


def test_counting_numbers_follow_book_t():
    # "For Knights, Queens and Princes, count 4. For Princesses, count 7. For Aces, count 11.
    # For small cards, count according to the number. For trumps, count 3 for the elemental
    # trumps; 9 for the planetary trumps; 12 for the Zodiacal trumps."
    assert [book_t.count_value(card(t)) for t in ("Knight of Wands", "Queen of Cups", "Prince of Swords",
                                                  "Princess of Disks", "Ace of Cups", "2 of Disks",
                                                  "10 of Swords")] == [4, 4, 4, 7, 11, 2, 10]
    majors = {c["title"].split(" - ", 1)[1]: book_t.count_value(c) for c in DECK if c["arcana_type"] == "Major"}
    assert {n for n, v in majors.items() if v == 3} == {"The Fool", "The Hanged Man", "The Aeon"}
    assert {n for n, v in majors.items() if v == 9} == {"The Magus", "The Priestess", "The Empress",
                                                         "Fortune", "The Tower", "The Sun", "The Universe"}
    assert sum(v == 12 for v in majors.values()) == 12
    assert all(book_t.count_value(c) for c in DECK)


# A ring of seven worked by hand. The Queen of Cups (index 1) is the significator.
PILE = [card(t) for t in ("3 of Cups", "Queen of Cups", "5 of Wands", "Ace of Swords",
                          "2 of Disks", "0 - The Fool", "4 of Cups")]


def test_count_includes_the_card_counted_from_and_stops_at_a_repeat():
    # Rightwards: Queen 4 -> three on = 2 of Disks (4); 2 -> one on = Fool (5); 3 -> two on,
    # round the ring = 3 of Cups (0); 3 -> 5 of Wands (2); 5 -> four on = 4 of Cups (6);
    # 4 -> three on = 5 of Wands again: stop.
    assert book_t.count_chain(PILE, 1, +1) == ([1, 4, 5, 0, 2, 6], 2)
    # Leftwards: Queen -> Fool (5); 3 -> Ace (3); 11 = ten on, three round a ring of 7 ->
    # 3 of Cups (0); 3 -> Fool again: stop.
    assert book_t.count_chain(PILE, 1, -1) == ([1, 5, 3, 0], 5)


def test_a_card_that_counts_round_the_whole_ring_ends_the_count():
    pile = [card("Princess of Cups"), card("2 of Cups"), card("3 of Swords")]   # 7 = 2 rounds + 1
    assert book_t.count_chain(pile, 0, +1) == ([0], None)


def test_pairs_work_outwards_from_the_significator():
    assert book_t.pair_round(PILE, 1) == ([(0, 2), (6, 3), (5, 4)], None)
    pairs, leftover = book_t.pair_round(PILE[:6], 1)       # five others: one left over
    assert pairs == [(0, 2), (5, 3)] and leftover == 4


def test_four_packs_are_ihvh_from_right_to_left():
    deck = list(range(78))
    packs = book_t.four_packs([{"card_id": i} for i in deck])
    # Top half to the left, each half cut again with its top to the left; I H V H from the right.
    assert [(p[0]["card_id"], p[-1]["card_id"]) for p in packs] == [(57, 77), (38, 56), (19, 37), (0, 18)]
    assert sum(len(p) for p in packs) == 78


def test_stacks_are_dealt_one_card_each_in_turn():
    stacks = book_t.deal_stacks(list(range(78)), 12)
    assert stacks[0][:3] == [0, 12, 24] and stacks[11][:2] == [11, 23]
    assert sorted(len(s) for s in stacks) == [6] * 6 + [7] * 6


def test_operation_four_is_the_significator_and_the_36_cards_after_it():
    sig = card("Queen of Cups")
    deck = [c for c in DECK if c is not sig]
    deck.insert(70, sig)                                   # near the bottom: the ring wraps
    op = book_t.operation_four(deck, sig)
    assert len(op["pile"]) == 37 and op["pile"][0] is sig and op["start"] == 0
    assert op["pile"][1] is deck[71] and op["pile"][8] is deck[0] and op["wrapped"]


def test_facing_sets_the_direction():
    sig = card("Queen of Cups")
    assert book_t.direction(sig, {}) == -1                                   # front: right to left
    assert book_t.direction(sig, {sig["title"]: "right"}) == 1
    assert book_t.direction(sig, {sig["title"]: "left"}) == -1


EXPECT = {"pack": 1, "house": (6, 4), "sign": (3, 7), "sephira": 5}


def test_strict_reading_stops_where_book_t_abandons():
    sig = card("Queen of Cups")
    statuses = set()
    for seed in range(300):
        ops = book_t.opening_of_the_key(DECK, seed, sig, EXPECT, strict=True)
        assert ops == book_t.opening_of_the_key(DECK, str(seed), sig, EXPECT, strict=True)   # same seed, same reading
        assert all(o["status"] == "read" for o in ops[:-1])
        if ops[-1]["status"] == "abandoned":
            assert ops[-1]["op"] in (1, 2, 3)
        else:
            assert [o["op"] for o in ops] == [1, 2, 3, 4, 5]
        for o in ops:
            statuses.add((o["op"], o["status"]))
            if o["status"] == "read":
                assert o["pile"][o["start"]] is sig and o["chain"][0] == o["start"]
                if o["op"] == 1:
                    assert o["place"]["index"] == 1
                if o["op"] in (2, 3):
                    assert o["place"] in (o["expected"], o["cognate"])
    assert (1, "abandoned") in statuses and (1, "read") in statuses


def test_lenient_reading_reads_every_operation_and_marks_the_misses():
    sig = card("Queen of Cups")
    for seed in range(100):
        ops = book_t.opening_of_the_key(DECK, seed, sig, EXPECT)   # the default reads on
        assert [o["op"] for o in ops] == [1, 2, 3, 4, 5]
        assert all(o["status"] in ("read", "missed") for o in ops)
        for o in ops:
            assert o["pile"][o["start"]] is sig


def test_significator_must_be_in_the_deck():
    with pytest.raises(ValueError):
        book_t.opening_of_the_key(DECK[1:], 1, DECK[0], EXPECT)


def test_positions_start_each_operation_at_the_significator():
    # The hand-worked ring above, read as Operation 5 in the 6th Sephira.
    o = book_t._read_pile(5, 5, PILE, card("Queen of Cups"), {"Queen of Cups": "right"}, expected=5, as_expected=True)
    placed = book_t.positions([o])
    assert [c["title"] for _, c in placed] == [PILE[(1 + k) % 7]["title"] for k in range(7)]
    assert placed[0][0] == "[Op 5] 6. Tiphareth: the Significator"
    assert placed[3][0] == "[Op 5] 6. Tiphareth: 3 to the right of the Significator"
    # Chain [1,4,5,0,2,6] stopping on 2, renumbered from the Queen (index 1 -> 0).
    assert o["chain_at"] == [0, 3, 4, 6, 1, 5] and o["stop_at"] == 1 and o["leftover_at"] is None
    # Pairs then depend only on the pile's size: either side of position 0 first.
    from ootk.spreads import book_t_pairs
    assert book_t_pairs(7) == [(6, 1), (5, 2), (4, 3)]
    assert book_t_pairs(8) == [(7, 1), (6, 2), (5, 3)]       # 4 is left over


def test_status_lines_say_what_book_t_would_do():
    sig = card("Queen of Cups")
    ops = book_t.opening_of_the_key(DECK, "408850", sig,
                                    {"pack": 1, "house": (9, 5), "sign": (9, None), "sephira": 5})
    lines = [book_t.status_line(o) for o in ops]
    assert lines[0].startswith("The question is about the Heh pack (love, marriage, pleasure), but")
    assert "abandon" in lines[0] and "the 10th house or the 6th house" in lines[1]
    assert lines[2].startswith("The Significator was not in Capricorn.")
    assert lines[3].startswith("Book T sets the Significator down")
    assert lines[4] == "The Significator is in 6. Tiphareth, the Sephira expected for this question."
    hit = dict(ops[1], status="read", found_in="cognate")
    assert "the related place tried next" in book_t.status_line(hit)


def test_expected_places_are_typed_from_one():
    assert book_t.parse_expect("2, 7/1, 4, 6") == {"pack": 1, "house": (6, 0), "sign": (3, None),
                                                   "sephira": 5}
    for bad in ("1,2,3", "0,1,1,1", "1,13,1,1", "1,1,1,11", "1,7/7,1,1", "x,1,1,1", ""):
        with pytest.raises(ValueError):
            book_t.parse_expect(bad)
