"""The report's "Your AI's answer" box: the page carries it, and its card-name matcher
(static/js/ai-answer.js) links the right cards. The matcher runs under node when node is
installed; the answer itself never reaches the server, so there is nothing server-side to test."""
import json
import pathlib
import shutil
import subprocess

import pytest

from test_app_and_engine import client, post  # noqa: F401  (fixture)

JS = pathlib.Path(__file__).resolve().parent.parent / "static" / "js" / "ai-answer.js"


def test_report_has_the_answer_box_before_the_summary(client):  # noqa: F811
    page = post(client).text
    assert page.index('id="nowStep"') < page.index('id="aiAnswer"') < page.index('id="summary"')
    assert 'id="answerInput"' in page and "js/ai-answer.js" in page
    assert "never sent to the site" in page
    # Nothing posts the answer anywhere: the box is not inside a form.
    box = page[page.index('id="aiAnswer"'):page.index('id="summary"')]
    assert "<form" not in box and 'name="' not in box


def run_node(script):
    if not shutil.which("node"):
        pytest.skip("node is not installed")
    out = subprocess.run(["node", "-e", f"const a = require({json.dumps(str(JS))});\n{script}"],
                         capture_output=True, text=True, check=True, timeout=30)
    return json.loads(out.stdout)


def test_card_names_match_thoth_and_waite_names():
    text = ("The Magus sits first, then the Two of Pentacles and the KNIGHT of the Wands. "
            "Wheel of Fortune turns; the art of waiting; Temperance; The Sun in Scorpio; "
            "Princess of Disks, Prince of Cups, 10 of swords. A King of Cups and the Page of Wands.")
    found = run_node(f"console.log(JSON.stringify(a.findCards({json.dumps(text)}).filter(p => p.key)"
                     ".map(p => [p.text, p.key])))")
    assert found == [["The Magus", "the magus"], ["Two of Pentacles", "2 of disks"],
                     ["KNIGHT of the Wands", "knight of wands"], ["Wheel of Fortune", "fortune"],
                     ["Temperance", "art"], ["The Sun", "the sun"], ["Princess of Disks", "princess of disks"],
                     ["Prince of Cups", "prince of cups"], ["10 of swords", "10 of swords"]]
    # Lower-case "art" is a word, not Atu XIV; Waite Kings and Pages are left alone.


def test_check_lists_named_missing_and_not_drawn_cards():
    titles = ["I - The Magus", "2 of Disks - Change", "IX - The Hermit", "Knight of Wands"]
    text = "The Magus and the 2 of Disks, then Death."
    r = run_node(f"const keys = {json.dumps(titles)}.map(a.cardKey);"
                 f"console.log(JSON.stringify(a.checkAnswer({json.dumps(text)}, keys)))")
    assert r == {"mentioned": ["the magus", "2 of disks"], "missing": ["the hermit", "knight of wands"],
                 "notDrawn": ["death"]}
    labels = run_node('console.log(JSON.stringify(["the hermit", "2 of disks", "knight of wands"].map(a.keyLabel)))')
    assert labels == ["The Hermit", "2 of Disks", "Knight of Wands"]
