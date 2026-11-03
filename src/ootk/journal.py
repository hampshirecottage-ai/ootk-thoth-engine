"""The private prediction journal (/admin/journal): does a reading drawn for a real question fit
what later happens better than a decoy reading drawn the same way for the same question?

Each entry draws two readings for one question: the real one, and a decoy from its own random
seed. The site owner pastes both prompts into an AI as Reading A and Reading B without knowing
which is which, saves the two answers, and once the question has settled writes down what
happened before seeing them again. Then the answers are shown once more, in a fresh random
order, for a blind pick. If readings carry nothing, the real one is picked about half the time.
"""
import re
from math import comb

# The site's two questions about the pick, in the order the results table lists them.
CHOICES = ("real", "decoy")
NEEDED = 67     # settled entries to see a 65% win rate against 50% (one-sided 5%, 80% power)
ANSWER_MAX = 60000
OUTCOME_MAX = 10000

_SEED_LINE = re.compile(r"^\*\*PRNG Seed:\*\* .*$", re.MULTILINE)
_STATEMENTS = re.compile(r"(?im)^[#*\s]*checkable statements\b")


def journal_prompt(prompt, settle_by, end_marker):
    """The reading's prompt as the journal sends it: its seed hidden (a remembered seed would
    say which reading is the real one) and, before its last line, a request for checkable
    statements about the settle-by date."""
    when = f"{settle_by:%-d %B %Y}"
    prompt = _SEED_LINE.sub("**PRNG Seed:** hidden for a blind check", prompt, count=1)
    ask = ("\n**Journal check:** this reading is part of a private prediction journal that will "
           f"be checked on {when}. After the Plain-Language Recap, add a section headed "
           "**Checkable statements** with 3 to 5 specific statements about what will have "
           f"happened or be true by {when}, each one that could later be marked true or false. "
           "Avoid statements that would fit almost anyone or any outcome.\n\n")
    head, sep, tail = prompt.rpartition(end_marker)
    return head + ask + sep + tail if sep else prompt + ask


def statements(answer):
    """The answer's Checkable statements section, or the whole answer when it has none."""
    answer = answer or ""
    found = _STATEMENTS.search(answer)
    return (answer[found.start():] if found else answer).strip()


def answers_by_role(entry):
    """{"real": answer, "decoy": answer} from the A/B answers saved in that order."""
    a, b = entry.get("answer_a") or "", entry.get("answer_b") or ""
    return {"real": a, "decoy": b} if entry["real_is_a"] else {"real": b, "decoy": a}


def stage(entry):
    """Where an entry stands: "answers" (waiting for the two AI answers), "waiting" (for its
    date or its outcome), "judge" (outcome written, blind pick to make) or "done"."""
    if not (entry.get("answer_a") and entry.get("answer_b")):
        return "answers"
    if not entry.get("outcome"):
        return "waiting"
    return "done" if entry.get("picked") else "judge"


def p_value(wins, n):
    """One-sided chance of `wins` or more real picks in `n` if picks were coin flips."""
    return sum(comb(n, k) for k in range(wins, n + 1)) / 2 ** n if n else 1.0


def results(entries):
    """The journal's score so far, from the entries that have a blind pick."""
    judged = [e for e in entries if e.get("picked")]
    n = len(judged)
    wins = sum(e["picked"] == "real" for e in judged)
    def mean(key):
        values = [e[key] for e in judged if e.get(key)]
        return round(sum(values) / len(values), 2) if values else None
    return {"judged": n, "real_picked": wins, "rate": round(wins / n, 2) if n else None,
            "p_value": round(p_value(wins, n), 3) if n else None,
            "rating_real": mean("rating_real"), "rating_decoy": mean("rating_decoy"),
            "needed": NEEDED, "open": sum(stage(e) != "done" for e in entries)}
