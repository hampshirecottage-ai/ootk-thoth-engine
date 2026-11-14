"""The private reading journal: encryption, the date finder, the timeline layout, and (with
OOTK_TEST_DB=1) the whole flow against a real database: start from a report, paste an answer,
see its dates on the timeline, export, delete."""
import os
import re
from datetime import date, datetime, timezone

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from ootk import journal
from ootk import web as app_module
from test_app_and_engine import client, post  # noqa: F401  (fixture)


@pytest.fixture
def key(monkeypatch):
    monkeypatch.setenv("JOURNAL_KEY", Fernet.generate_key().decode())


def test_texts_are_encrypted_and_a_changed_key_reads_as_a_note(key, monkeypatch):
    token = journal.seal("The Tower, then calm.")
    assert "Tower" not in token and journal.unseal(token) == "The Tower, then calm."
    assert journal.seal("") is None and journal.unseal(None) == ""
    monkeypatch.setenv("JOURNAL_KEY", Fernet.generate_key().decode())
    assert "can't be read" in journal.unseal(token)


def test_only_a_hash_of_the_journal_key_is_kept():
    k = journal.new_key()
    assert re.fullmatch(journal.KEY_PATTERN, k)
    assert journal.key_hash(k) != k and len(journal.key_hash(k)) == 64


ANSWER = """## Timing

- **Peace**: Nov 12 to Nov 22
- Swiftness falls (Nov 21 to Nov 30)
- Power runs 22 Nov – 21 Dec
* Pisces window: Feb 19 to Mar 20
Turning point (Art): August 2nd through August 12th
Expect news around 3-9 Jan.
Already open: Oct 25 to Nov 14"""


def test_dates_in_an_answer_become_named_windows_after_the_draw():
    found = journal.find_windows(ANSWER, date(2026, 11, 13))
    assert found == [
        ("Peace", date(2026, 11, 12), date(2026, 11, 22)),
        ("Swiftness falls", date(2026, 11, 21), date(2026, 11, 30)),
        ("Power", date(2026, 11, 22), date(2026, 12, 21)),
        ("Pisces window", date(2027, 2, 19), date(2027, 3, 20)),
        ("Turning point (Art)", date(2027, 8, 2), date(2027, 8, 12)),
        ("Expect news", date(2027, 1, 3), date(2027, 1, 9)),
        ("Already open", date(2026, 10, 25), date(2026, 11, 14)),
    ]
    assert journal.find_windows("No dates here. Feb 30 to Feb 31 isn't real.", date(2026, 1, 1)) == []


def entry(entry_id, thread_id, drawn, **over):
    return dict(entry_id=entry_id, thread_id=thread_id, drawn_at=datetime(*drawn, tzinfo=timezone.utc),
                link=f"link{entry_id}", question="Q?", spread_key="3", answer_ai="Claude",
                card_titles=["XIV - Art", "2 of Swords - Peace"], **over)


def test_timeline_rows_follow_the_threads_with_positions_in_the_span():
    threads = [{"thread_id": 1, "name": "Relationships"}]
    entries = [entry(10, 1, (2026, 11, 13)), entry(11, None, (2026, 12, 1))]
    windows = [{"entry_id": 10, "label": "Peace", "starts": date(2026, 11, 12), "ends": date(2026, 11, 22)},
               {"entry_id": 10, "label": "One day", "starts": date(2027, 3, 1), "ends": date(2027, 3, 1)}]
    t = journal.build_timeline(threads, entries, windows, date(2026, 11, 13))
    assert t["start"] == date(2026, 11, 1) and t["months_count"] == 12
    assert [m["label"] for m in t["months"]][:3] == ["Nov", "Dec", "Jan"]
    assert {s["name"] for s in t["signs"]} == {name for name, _ in journal.SIGNS}
    assert [g["name"] for g in t["groups"]] == ["Relationships", "Not in a thread"]
    peace, one_day = t["groups"][0]["rows"]
    assert peace["kind"] == "bar" and 0 < peace["left"] < 5 and peace["width"] > 0
    assert peace["element"] == "water"            # 12 Nov: the Sun in Scorpio
    assert one_day["kind"] == "dot" and one_day["when"] == "1 Mar 2027"
    (drawn,) = t["groups"][1]["rows"]              # a reading with no dates: a dot on its day
    assert drawn["kind"] == "reading" and drawn["link"] == "link11"


def test_export_lists_each_thread_and_its_answers():
    e = entry(10, 1, (2026, 11, 13), answer="It looks calm.", notes="", outcome="It was.",
              outcome_at=datetime(2026, 12, 1), added_at=datetime(2026, 11, 13))
    text = journal.export_markdown([{"thread_id": 1, "name": "Relationships"}], [e])
    assert "## Relationships" in text and "It looks calm." in text and "It was." in text
    assert "Not in a thread" not in text


def test_without_a_key_there_is_no_journal(client, monkeypatch):  # noqa: F811
    monkeypatch.delenv("JOURNAL_KEY", raising=False)
    assert client.get("/journal").status_code == 404
    assert 'id="journalBox"' not in post(client).text
    assert 'href="/journal"' not in client.get("/start").text


def test_the_report_offers_a_journal_without_touching_the_database(client, key):  # noqa: F811
    page = post(client).text
    assert 'id="journalBox"' in page and 'action="/journal/start"' in page
    assert 'href="/journal"' in client.get("/start").text


def test_journal_links_are_kept_out_of_the_logs():
    record = type("R", (), {"args": ("1.2.3.4", "GET", "/journal/k/abcdefghijklmnopqrstuvwxyz012345", "1.1", 303)})()
    app_module.RedactReportLinks().filter(record)
    assert record.args[2] == "/journal/k/<redacted>"
    assert app_module.is_private_path("/journal/entry/3")


# ---------- the whole flow, against a real database ----------

needs_db = pytest.mark.skipif(os.getenv("OOTK_TEST_DB") != "1", reason="set OOTK_TEST_DB=1 to run against a real database")


def draw(c, topic="Will the move go well?", seed="408850"):
    r = c.post("/generate_report", data={"spread_key": "3", "seed": seed, "topic": topic,
                                         "mapping_system": "thoth", "framework": "auto", "draw_mode": "seed"},
               follow_redirects=False)
    assert r.status_code == 303
    return r.headers["location"].rsplit("/", 1)[1]


@needs_db
def test_journal_flow_from_report_to_timeline_and_delete(key):
    from ootk import db
    c = TestClient(app_module.app)
    link = draw(c)
    assert 'action="/journal/start"' in c.get(f"/report/{link}").text
    r = c.post("/journal/start", data={"link": link}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].startswith("/journal/entry/")
    entry_url = r.headers["location"].split("?")[0]
    jkey = c.cookies.get("ootk_journal")
    assert jkey and "httponly" in r.headers["set-cookie"].lower()

    # The first answer pasted puts its dates on the timeline.
    page = c.post(entry_url, data={"answer": ANSWER, "answer_ai": "Claude", "thread": "new",
                                   "new_thread": "Relationships", "windows_shown": "0"}).text
    assert 'value="Pisces window"' in page and "Saved." in page
    timeline = c.get("/journal/timeline").text
    assert "Pisces window" in timeline and f"/report/{link}" in timeline and "Relationships" in timeline

    # The report now says the reading is in the journal; a second reading files into the thread.
    assert "This reading is in your journal." in c.get(f"/report/{link}").text
    second = draw(c, "Where next?", "100020")
    thread_id = re.search(r'<option value="(\d+)">Relationships</option>', c.get(f"/report/{second}").text).group(1)
    assert c.post("/journal/add", data={"link": second, "thread": thread_id}).status_code == 200
    assert c.get(f"/journal/thread/{thread_id}").text.count('class="j-entry"') == 2

    # Stored encrypted: neither the answer nor the thread name is readable in the database.
    with db.get_db_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT answer FROM reading_journal_entries WHERE answer IS NOT NULL;")
        assert all("Pisces" not in row["answer"] for row in cur.fetchall())
        cur.execute("SELECT name, label FROM reading_journal_threads, reading_journal_windows LIMIT 5;")
        assert all("Relationships" not in row["name"] and "Pisces" not in row["label"] for row in cur.fetchall())

    assert "Pisces window" in c.get("/journal/export.md").text

    # Another browser sees nothing without the link; with it, the same journal.
    other = TestClient(app_module.app)
    assert other.get(entry_url, follow_redirects=False).headers["location"] == "/journal"
    assert other.get(f"/journal/k/{jkey}", follow_redirects=False).status_code == 303
    assert "Relationships" in other.get("/journal").text

    # A form from another site is refused.
    assert c.post("/journal/delete", headers={"origin": "https://evil.example"}).status_code == 403

    c.post("/journal/delete")
    assert c.get(f"/journal/k/{jkey}", follow_redirects=False).status_code == 404
    with db.get_db_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) AS n FROM reading_journals WHERE key_hash = %s;", (journal.key_hash(jkey),))
        assert cur.fetchone()["n"] == 0


def test_the_timeline_list_the_prompt_asks_for_is_read_first():
    answer = ("The tide turns Nov 12 to Nov 22.\n\n## Plain-Language Recap\nGo ahead.\n\n## Timeline\n"
              "- Move goes ahead: 2026-12-01 to 2026-12-21\n- **Contract signed:** 2027-01-15\n"
              "- Pisces window 2027-02-19 – 2027-03-20\n\n## Notes\n- Later: 2028-01-01\n")
    assert journal.find_windows(answer, date(2026, 11, 13)) == [
        ("Move goes ahead", date(2026, 12, 1), date(2026, 12, 21)),
        ("Contract signed", date(2027, 1, 15), date(2027, 1, 15)),
        ("Pisces window", date(2027, 2, 19), date(2027, 3, 20))]
    # No list with dates in it: dates anywhere in the answer are still found.
    assert journal.find_windows("## Timeline\n- none\n\nThe tide turns Nov 12 to Nov 22.", date(2026, 11, 13)) == [
        ("The tide turns", date(2026, 11, 12), date(2026, 11, 22))]


def test_the_prompt_asks_for_a_timeline_list():
    with open(os.path.join(os.path.dirname(__file__), "prompt_snapshots", "spread_3.md"), encoding="utf-8") as f:
        text = f.read()
    assert "`## Timeline`" in text and "YYYY-MM-DD to YYYY-MM-DD" in text


def test_the_cards_own_decan_dates_match_the_prompts_year():
    drawn = datetime(2026, 11, 13, tzinfo=timezone.utc)
    titles = ["8 of Wands - Swiftness", "9 of Disks - Gain", "Ace of Cups", "8 of Wands - Swiftness", "Prince of Swords"]
    # The 9 of Disks' decan (September) is past by 13 November, so its next one is given.
    assert journal.card_windows(titles, drawn) == [
        ("8 of Wands decan", date(2026, 11, 22), date(2026, 12, 2)),
        ("9 of Disks decan", date(2027, 9, 2), date(2027, 9, 12))]


@needs_db
def test_find_dates_button_shows_dates_for_checking_without_saving_them(key):
    c = TestClient(app_module.app)
    link = draw(c, seed="100020")
    entry_url = c.post("/journal/start", data={"link": link}, follow_redirects=False).headers["location"].split("?")[0]
    answer = "Text.\n\n## Timeline\n- Move goes ahead: 2026-12-01 to 2026-12-21\n"
    r = c.post(entry_url, data={"answer": answer, "action": "find", "windows_shown": "1"}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "?find=1#windowsTitle"
    page = c.get(entry_url + "?find=1").text
    assert "Found 1 date in the answer" in page and 'value="Move goes ahead"' in page
    # Saved answer, but nothing is on the timeline until Save.
    assert "Move goes ahead" not in c.get("/journal/timeline").text
    assert "Text." in c.get(entry_url).text
    c.post("/journal/delete")


def test_a_timeline_copied_as_plain_text_from_a_chat_app_is_found():
    # Chat apps copy rendered text: the heading loses its ##, the line its bullet, and the
    # name can carry a colon and an aside in brackets before the dates.
    answer = ("Plain-language recap. It looks likely, after a pause.\n"
              "Timeline\n"
              "the pause, then the move (the cards give no date; this matches the earlier reading): "
              "2026-11-13 to 2027-03-31\n"
              "Advice / action points\n"
              "Say it once, kindly.\n"
              "A later note 2028-01-01 to 2028-02-01\n")
    assert journal.find_windows(answer, date(2026, 11, 13)) == [
        ("The pause, then the move", date(2026, 11, 13), date(2027, 3, 31))]


def test_iso_dates_are_found_even_without_a_timeline_list():
    assert journal.find_windows("Expect news 2026-12-01 to 2026-12-21.", date(2026, 11, 13)) == [
        ("Expect news", date(2026, 12, 1), date(2026, 12, 21))]
