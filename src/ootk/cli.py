"""Command-line entry point: `ootk` (or `python -m ootk`)."""
import argparse
import sys

import psycopg

from ootk.db import (
    CardNotFound, DEFAULT_MAPPING, MAPPING_SYSTEMS, DatabaseOutdated, fetch_all_cards, get_db_connection, load_cards_data, load_withheld, save_spread_session,
)
from ootk.report import analyze_reading, generate_html_output
from ootk.shuffle import (
    draw_spread, duplicate_in_operation, has_significator_position, operation_number, resolve_significator,
)
from ootk.significator import RANKS, SUITS, book_t_card
from ootk.spreads import SPREADS, spread_positions

class CliError(Exception):
    """A problem with the command line or the answers given; printed without a traceback."""


def parse_args():
    parser = argparse.ArgumentParser(description="Thoth Tarot & Liber 777 Calculation Engine")
    parser.add_argument("--topic", type=str, help="Query or topic intent string", default=None)
    parser.add_argument("--seed", type=str, help="PRNG numeric seed for deterministic draws", default=None)
    parser.add_argument("--significator", type=str, default=None,
                        help="Significator card title, pinned to position 1 of OOTK Op 1 (e.g. 'Queen of Cups')")
    parser.add_argument("--spread", type=str, help="Spread key (1-12)", default=None)
    parser.add_argument("--framework", type=str, choices=["auto", "light_descent", "soul_formation", "life_path", "post_mortem"], default="auto", help="Override Macro Conceptual Framework (auto picks light_descent, post_mortem or life_path from the draw; soul_formation is manual only)")
    parser.add_argument("--mapping", type=str, choices=MAPPING_SYSTEMS, default=DEFAULT_MAPPING, help="Tarot-Kabbalah mapping scheme: thoth keeps Crowley's swap (Emperor on Tzaddi, Star on Heh), golden_dawn undoes it")
    parser.add_argument("--html", action="store_true", help="Auto-generate HTML report in output/")
    return parser.parse_args()

def ask_significator():
    """Book T: the court card matching the querent's age, gender and colouring, or any title typed."""
    print("\nThis spread needs a significator. Press ENTER at the first question to type a card instead.")
    ranks, suits = list(RANKS), list(SUITS)
    for idx, rank in enumerate(ranks, start=1):
        print(f" [{idx}] {RANKS[rank]} ({rank})")
    choice = input("Who is the reading for? ").strip()
    if not choice:
        title = ""
        while not title:
            title = input("Significator card title: ").strip()
        return title
    while choice not in {"1", "2", "3", "4"}:
        choice = input("Enter 1-4: ").strip()
    rank = ranks[int(choice) - 1]
    for idx, suit in enumerate(suits, start=1):
        print(f" [{idx}] {SUITS[suit]} ({suit})")
    choice = input("Colouring or temperament: ").strip()
    while choice not in {"1", "2", "3", "4"}:
        choice = input("Enter 1-4: ").strip()
    return book_t_card(rank, suits[int(choice) - 1])

def display_card_selection(cards):
    print("\n--- AVAILABLE THOTH CARDS ---")
    for idx, card in enumerate(cards, start=1):
        print(f"{idx:2d}. {card['title']} (Card ID {card['card_id']})")

def run_spread_session():
    args = parse_args()
    # The web form strips the seed, so ' 42' must draw what 42 draws there.
    args.seed = (args.seed or "").strip() or None
    if args.spread is not None and args.spread.strip() not in SPREADS:
        raise CliError(f"Unknown spread {args.spread!r}. Use a number from 1 to {len(SPREADS)}.")
    args.spread = args.spread.strip() if args.spread else None

    # Two short connections, not one held open while the questions below wait for answers:
    # a hosted database (Neon) can drop a connection that sits idle, and the save would fail.
    with get_db_connection() as conn:
        cards = fetch_all_cards(conn)
    card_lookup = {str(idx): card["title"] for idx, card in enumerate(cards, start=1)}
    card_titles_set = {card["title"].lower(): card["title"] for card in cards}

    print("==================================================")
    print("       THOTH TAROT & LIBER 777 ENGINE           ")
    print("==================================================")

    if args.spread:
        spread_choice = args.spread
    else:
        print("Select a spread layout:\n")
        print("--- CORE & PROGRESSIVE SPREADS ---")
        for key in ["1", "2", "3", "4", "5"]:
            print(f" [{key:2s}] {SPREADS[key]['name']} ({len(SPREADS[key]['positions'])} cards)")
            
        print("\n--- HERMETIC & MACROCOSMIC LAYOUTS ---")
        for key in ["6", "7"]:
            print(f" [{key:2s}] {SPREADS[key]['name']} ({len(SPREADS[key]['positions'])} cards)")

        print("\n--- OPENING OF THE KEY (OOTK) OPERATIONS ---")
        for key in ["8", "9", "10", "11"]:
            print(f" [{key:2s}] {SPREADS[key]['name']} ({len(SPREADS[key]['positions'])} cards)")

        print("\n--- MASTER PIPELINE ---")
        print(f" [12] {SPREADS['12']['name']} (75 cards total, reshuffled for each operation)")

        spread_choice = input("\nEnter spread number (1-12): ").strip()
        while spread_choice not in SPREADS:
            spread_choice = input("Invalid spread. Enter a number from 1 to 12: ").strip()

    selected_spread = SPREADS[spread_choice]
    print(f"\n---> Selected Spread: {selected_spread['name']}\n")

    query_prompt = args.topic if args.topic else (input("Enter Query / Intent Prompt (optional, press ENTER to skip): ").strip() or None)
    session_notes = f"PRNG Seed: {args.seed}" if args.seed else (input("Enter Session Notes (optional, press ENTER to skip): ").strip() or None)
    significator = args.significator

    spread_results = []

    target_positions = spread_positions(spread_choice)

    if not significator and has_significator_position(target_positions):
        significator = ask_significator()
    sig_card = resolve_significator(cards, significator)
    if significator and sig_card is None:
        raise CliError(f"Significator '{significator}' not found in thoth_cards.")

    # Only pin when the spread actually has a significator position (first position).
    pin_significator = bool(sig_card) and has_significator_position(target_positions)
    # Same draw as the web GUI for the same seed (see ootk.shuffle.draw_spread).
    try:
        seeded_titles = draw_spread(cards, args.seed, target_positions, sig_card)[0] if args.seed else None
    except ValueError as e:
        raise CliError(str(e)) from e
    significator_label = (
        sig_card["title"] if pin_significator
        else "None (spread has no significator position)"
    )

    selected_titles = []
    for pos_idx, position_name in enumerate(target_positions, start=1):
        print(f"\n[Position {pos_idx}: {position_name}]")
        
        if pin_significator and pos_idx == 1:
            selected_title = sig_card["title"]
            print(f"--> Significator (pinned): {selected_title}")
        elif seeded_titles:
            selected_title = seeded_titles[pos_idx - 1]
            print(f"--> PRNG Auto-Drawn: {selected_title}")
        else:
            selected_title = None
            while not selected_title:
                user_input = input("Enter card index number (or type full name): ").strip()
                if user_input in card_lookup:
                    selected_title = card_lookup[user_input]
                elif user_input.lower() in card_titles_set:
                    selected_title = card_titles_set[user_input.lower()]
                else:
                    print("Invalid card selection. Type 'list' or try again.")
                    if user_input.lower() == 'list':
                        display_card_selection(cards)
                if selected_title and duplicate_in_operation(
                        target_positions[:pos_idx], selected_titles + [selected_title]):
                    # One deck per operation: a card can't fall twice in it (the web form
                    # refuses it too). A master pipeline reshuffles for each operation.
                    op = operation_number(position_name)
                    earlier = next(i for i, (p, t) in enumerate(zip(target_positions, selected_titles), start=1)
                                   if t == selected_title and operation_number(p) == op)
                    print(f"{selected_title} is already at position {earlier}. Choose another card.")
                    selected_title = None

        selected_titles.append(selected_title)

    with get_db_connection() as conn:
        # One query for the whole draw instead of one per position.
        for pos_idx, (position_name, card_data) in enumerate(
                zip(target_positions, load_cards_data(conn, selected_titles, args.mapping)), start=1):
            spread_results.append({
                "position_number": pos_idx,
                "position_name": position_name,
                "card_data": card_data
            })

        withheld = load_withheld(conn, cards, selected_titles, args.mapping)
        reading = analyze_reading(
            selected_spread["name"], spread_choice, query_prompt, significator_label, args.seed,
            spread_results, framework=args.framework, mapping_system=args.mapping, withheld=withheld,
        )
        analytical_prompt = reading["analytical_prompt"]

        print("\n" + analytical_prompt)

        session_id = save_spread_session(conn, selected_spread["name"], query_prompt, session_notes, significator_label, spread_results, reading["dignity_matrix"])

        if args.html:
            generate_html_output(session_id, selected_spread["name"], query_prompt, analytical_prompt)


def main():
    try:
        run_spread_session()
    except (CliError, CardNotFound, DatabaseOutdated) as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
    except psycopg.OperationalError as e:
        print(f"[ERROR] Database connection failed: {e}", file=sys.stderr)
        sys.exit(1)
    except EOFError:
        print("\n[ERROR] Input ended before the reading was complete. To run without prompts, "
              "give --spread, --seed and --topic (and --significator for OOTK Op 1).", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
