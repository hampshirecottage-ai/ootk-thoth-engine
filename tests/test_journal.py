"""The private reading journal: encryption, the date finder, the timeline layout, and (with
OOTK_TEST_DB=1) the whole flow against a real database: start from a report, paste an answer,
see its dates on the timeline, export, delete."""
import os
import re
from datetime import date, datetime, timedelta, timezone

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from ootk import PROJECT_ROOT, journal
from ootk.lockout import FailedLogins
from ootk import web as app_module
from test_app_and_engine import client, post  # noqa: F401  (fixture)


@pytest.fixture
def key(monkeypatch):
    monkeypatch.setenv("JOURNAL_KEY", Fernet.generate_key().decode())
    # Each test starts its own journal from the one test address; a fresh count keeps the
    # five-an-hour limit on new journals from turning away the sixth test in a run.
    monkeypatch.setattr(app_module, "journal_starters", FailedLogins(attempts=5, window=3600))


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
    assert [g["name"] for g in t["groups"]] == ["Relationships", "Not in a question"]
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
    assert "Not in a question" not in text


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
    # Started from a report, the entry page shows the link to save; later visits don't.
    first = c.get(r.headers["location"]).text
    assert "Save your journal link" in first and f"/journal/k/{jkey}" in first
    assert "Save your journal link" not in c.get(entry_url).text

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
    # No Timeline list: dates anywhere in the answer are still found.
    assert journal.find_windows("## Recap\nGo.\n\nThe tide turns Nov 12 to Nov 22.", date(2026, 11, 13)) == [
        ("The tide turns", date(2026, 11, 12), date(2026, 11, 22))]
    # A list that says "- none" (the reading points to no particular time) means no dates,
    # in Markdown or pasted as plain text.
    for none in ("## Timeline\n- none\n\nThe tide turns Nov 12 to Nov 22.",
                 "Timeline\n\nNone.\n\nThe tide turns Nov 12 to Nov 22."):
        assert journal.find_windows(none, date(2026, 11, 13)) == []


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


def test_start_here_journal_section_shows_the_animation_with_a_still_for_reduced_motion(key, client):  # noqa: F811
    page = client.get("/start").text
    section = page[page.index('id="journalHelp"'):]
    section = section[:section.index("</details>")]
    assert 'id="journal-how-to"' in section and "site/journal-how-to.gif" in section
    assert 'media="(prefers-reduced-motion: reduce)"' in section and "site/journal-how-to-still.webp" in section
    site = PROJECT_ROOT / "static" / "site"
    assert (site / "journal-how-to.gif").read_bytes()[:6] == b"GIF89a"
    assert (site / "journal-how-to-still.webp").read_bytes()[8:12] == b"WEBP"


def test_dates_far_from_the_reading_stay_off_the_timeline():
    # A date from history in an answer, or a year typed as 202, is not a timing window.
    answer = "## Timeline\n- Hastings: 1066-10-14 to 1066-10-15\n- Move: 2026-12-01 to 2026-12-21\n"
    assert journal.find_windows(answer, date(2026, 11, 13)) == [
        ("Move", date(2026, 12, 1), date(2026, 12, 21))]
    assert journal.find_windows("Hastings 1066-10-14 to 1066-10-15.", date(2026, 11, 13)) == []
    assert journal.window_near(date(2036, 1, 1), date(2036, 2, 1), date(2026, 11, 13))
    assert not journal.window_near(date(2026, 1, 1), date(2037, 1, 1), date(2026, 11, 13))
    # Windows already saved with such years: the page still draws, spanning this year only.
    entries = [entry(10, None, (2026, 11, 13))]
    for odd in (date(1, 1, 1), date(202, 11, 20), date(9999, 12, 31)):
        windows = [{"entry_id": 10, "label": "Typo", "starts": odd, "ends": odd},
                   {"entry_id": 10, "label": "Peace", "starts": date(2026, 11, 12), "ends": date(2026, 11, 22)}]
        t = journal.build_timeline([], entries, windows, date(2026, 11, 13))
        assert t["start"] == date(2026, 11, 1)
        assert [r["label"] for r in t["groups"][0]["rows"]] == ["Peace"]


def test_windows_too_far_for_one_timeline_page_are_left_off_it():
    """A window may be saved up to 10 years from its reading, but a timeline page spans five
    years at most. One that doesn't fit is left off; today and the readings stay on the page,
    and the page isn't stretched toward it."""
    entries = [entry(10, None, (2026, 11, 13))]
    today = date(2026, 11, 21)
    peace = {"entry_id": 10, "label": "Peace", "starts": date(2026, 11, 12), "ends": date(2026, 11, 22)}
    later = {"entry_id": 10, "label": "Later", "starts": date(2030, 6, 1), "ends": date(2030, 6, 10)}
    for far in (date(2034, 6, 1), date(2018, 6, 1)):          # 8 years after, and before, the draw
        windows = [peace, later, {"entry_id": 10, "label": "Far", "starts": far, "ends": far + timedelta(days=9)}]
        t = journal.build_timeline([], entries, windows, today)
        assert t["start"] == date(2026, 11, 1) and t["end"] == date(2030, 7, 1)
        rows = t["groups"][0]["rows"]
        assert [r["label"] for r in rows] == ["Peace", "Later"]
        assert 0 < t["today"] < 5 and rows[1]["left"] < 100 and rows[1]["width"] > 0
        assert rows[1]["element"] == "air"                     # 1 June 2030: the Sun in Gemini
    # One that fits, years before the draw, still widens the page; today stays on it.
    early = {"entry_id": 10, "label": "Early", "starts": date(2023, 3, 1), "ends": date(2023, 3, 9)}
    t = journal.build_timeline([], entries, [early, peace], today)
    assert t["start"] == date(2023, 3, 1) and t["today"] < 100
    assert [r["label"] for r in t["groups"][0]["rows"]] == ["Early", "Peace"]


@needs_db
def test_a_date_far_from_the_reading_is_refused_on_the_entry_form(key):
    c = TestClient(app_module.app)
    link = draw(c, seed="100020")
    entry_url = c.post("/journal/start", data={"link": link}, follow_redirects=False).headers["location"].split("?")[0]
    form = {"answer": "Text.", "w_label": "Typo", "w_starts": "0202-11-20", "w_ends": "", "w_keep": "0"}
    r = c.post(entry_url, data=form, follow_redirects=False)
    assert r.status_code == 400 and "more than 10 years" in r.text
    r = c.post(entry_url, data=dict(form, w_starts="2027-03-01"), follow_redirects=False)
    assert r.status_code == 303
    assert "Typo" in c.get("/journal/timeline").text
    c.post("/journal/delete")


@needs_db
def test_adding_a_reading_with_no_question_to_a_journal_with_no_questions(key):
    """A journal with no questions yet and a reading drawn with no question: the report box
    offers "Not in a question yet" and filing it works, even from an older page that still
    sends a blank new question. A question longer than a question name is cut to fit."""
    c = TestClient(app_module.app)
    first = draw(c)
    assert c.post("/journal/start", data={"link": first}, follow_redirects=False).status_code == 303

    general = draw(c, "", "100020")
    page = c.get(f"/report/{general}").text
    assert '<option value="new" selected>' not in page and '<div id="jNewRow" hidden>' in page
    r = c.post("/journal/add", data={"link": general, "thread": "new", "new_thread": "  "},
               follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].startswith("/journal/entry/")
    home = c.get("/journal").text
    assert "Not in a question yet" in home and "<h2" in home.split("Not in a question yet")[0][-60:]

    long_question = "Will it " + "really " * 40 + "work out?"
    asked = draw(c, long_question, "100126")
    page = c.get(f"/report/{asked}").text
    assert '<option value="new" selected>' in page
    prefilled = re.search(r'id="jNew" name="new_thread" maxlength="200" value="([^"]*)"', page).group(1)
    assert len(prefilled) == 200
    r = c.post("/journal/add", data={"link": asked, "thread": "new", "new_thread": long_question},
               follow_redirects=False)
    assert r.status_code == 303
    assert "Will it really" in c.get("/journal").text
    c.post("/journal/delete")


def test_the_journal_cookie_asks_for_no_more_than_browsers_keep():
    # Chrome cuts a longer Max-Age to 400 days, so asking for more only hides when it runs out.
    assert app_module.JOURNAL_COOKIE_AGE == 400 * 24 * 3600


@needs_db
def test_journal_visits_renew_the_cookie_unchanged(key):
    """Each journal page shown renews the cookie with the same key and flags, so an active
    visitor never loses it; pages that turn the visitor away don't, and other pages don't."""
    c = TestClient(app_module.app, base_url="https://testserver")
    link = draw(c, seed="100020")
    r = c.post("/journal/start", data={"link": link}, follow_redirects=False)
    jkey = c.cookies.get("ootk_journal")
    for page in ("/journal", "/journal/timeline", r.headers["location"].split("?")[0], "/journal/export.md"):
        got = c.get(page, follow_redirects=False)
        assert got.status_code == 200, page
        cookie = got.headers.get("set-cookie", "")
        assert cookie.startswith(f"ootk_journal={jkey};"), page
        flags = cookie.lower()
        assert "max-age=34560000" in flags and "httponly" in flags and "samesite=lax" in flags and "secure" in flags
    assert "set-cookie" not in c.get(f"/report/{link}").headers
    # Without a journal: nothing set, and a cookie for a deleted journal is removed, not renewed.
    assert "set-cookie" not in TestClient(app_module.app).get("/journal").headers
    c.post("/journal/delete")
    stale = TestClient(app_module.app, cookies={"ootk_journal": jkey})
    got = stale.get("/journal")
    assert got.status_code == 200 and 'ootk_journal=""' in got.headers.get("set-cookie", "")
    assert stale.get("/journal/timeline", follow_redirects=False).headers.get("set-cookie") is None


@needs_db
def test_the_timeline_opens_scrolled_to_today(key):
    """The timeline marks today in its month row and, before anything else runs, scrolls a
    timeline wider than the screen so today shows (a third of the way across the dates)."""
    c = TestClient(app_module.app)
    link = draw(c, seed="100020")
    c.post("/journal/start", data={"link": link})
    page = c.get("/journal/timeline").text
    assert page.count('id="tlToday"') == 1
    script = page.split('id="tlToday"', 1)[1]
    assert script.index('getElementById("tlToday")') < script.index("One shared balloon")
    assert "tl.scrollLeft = Math.max(0, x - label.offsetWidth - dates / 3)" in script


def test_dates_unticked_and_saved_stay_off_the_timeline(key):
    """Untick every date and Save: reopening the entry doesn't offer them again ticked, and a
    later Save that only adds an outcome doesn't put them back."""
    c = TestClient(app_module.app)
    link = draw(c, seed="100020")
    entry_url = c.post("/journal/start", data={"link": link}, follow_redirects=False).headers["location"].split("?")[0]
    answer = "Text.\n\n## Timeline\n- Move goes ahead: 2026-12-01 to 2026-12-21\n"
    page = c.post(entry_url, data={"answer": answer, "windows_shown": "0"}).text
    assert 'value="Move goes ahead"' in page and "Move goes ahead" in c.get("/journal/timeline").text

    # The visitor unticks the one date (no w_keep) and saves.
    form = {"answer": answer, "w_label": ["Move goes ahead", "", ""], "w_starts": ["2026-12-01", "", ""],
            "w_ends": ["2026-12-21", "", ""], "windows_shown": "1"}
    c.post(entry_url, data=form)
    reopened = c.get(entry_url).text
    assert 'value="Move goes ahead"' not in reopened
    assert '<input type="hidden" name="windows_shown" value="1">' in reopened
    # A later Save from that page, adding only an outcome, keeps the timeline empty.
    c.post(entry_url, data={"answer": answer, "outcome": "We moved.", "w_label": ["", ""],
                            "w_starts": ["", ""], "w_ends": ["", ""], "w_keep": ["0", "1"],
                            "windows_shown": "1"})
    assert "Move goes ahead" not in c.get("/journal/timeline").text
    assert "We moved." in c.get(entry_url).text
    # Find dates still offers them again on request.
    assert 'value="Move goes ahead"' in c.get(entry_url + "?find=1").text


def test_a_journal_entry_may_send_a_long_answer_but_other_forms_keep_the_small_limit(client):  # noqa: F811
    """Saving an entry may send up to 1 MB (a 200,000-character answer); every other form keeps
    the 64 KB limit, and a post without a Content-Length is still refused unread."""
    long_answer = {"answer": "The cards say wait. " * 3_000}       # 60,000 characters
    # Past the size check (no journal key here, so the journal itself answers 404).
    assert client.post("/journal/entry/1", data=long_answer).status_code == 404
    assert client.post("/generate_report", data={"spread_key": "3", "topic": "q" * 70_000}).status_code == 413
    too_big = {"answer": "x" * (app_module.JOURNAL_ENTRY_BODY_BYTES + 1)}
    r = client.post("/journal/entry/1", data=too_big, headers={"accept": "text/html"})
    assert r.status_code == 413 and "This entry is too large" in r.text
    r = client.post("/journal/entry/1", content=b"answer=x", headers={"content-length": ""})
    assert r.status_code == 413


@needs_db
def test_a_60000_character_answer_is_saved(key):
    c = TestClient(app_module.app)
    link = draw(c, seed="100020")
    entry_url = c.post("/journal/start", data={"link": link}, follow_redirects=False).headers["location"].split("?")[0]
    answer = ("The cards say wait – then act. " * 2_000)[:60_000]
    r = c.post(entry_url, data={"answer": answer, "windows_shown": "1"}, follow_redirects=False)
    assert r.status_code == 303
    assert answer.strip()[-40:] in c.get(entry_url).text
    c.post("/journal/delete")


def test_entry_times_are_in_the_readings_own_time_zone():
    """The database gives UTC; an entry's dates are the day where the reading was drawn, as on
    its report. 17:17 in Vancouver on 17 Nov is 01:17 UTC on 18 Nov."""
    from datetime import datetime, timezone
    row = {"answer": None, "notes": None, "outcome": None, "card_titles": [], "tz": "America/Vancouver",
           "drawn_at": datetime(2026, 11, 18, 1, 17, tzinfo=timezone.utc),
           "added_at": datetime(2026, 11, 18, 1, 20, tzinfo=timezone.utc), "outcome_at": None}
    e = journal._entry(row)
    assert e["drawn_at"].date().isoformat() == "2026-11-17" and e["added_at"].day == 17
    assert "tz" not in e and e["outcome_at"] is None
    for zone in ("", None, "Not/AZone", "Europe", "x" * 200):    # unknown or missing: UTC as before
        assert journal._entry(dict(row, tz=zone))["drawn_at"].date().isoformat() == "2026-11-18"
    # Today follows the newest reading's zone: 01:17 UTC on 18 Nov is still the 17th in Vancouver.
    now = datetime(2026, 11, 18, 1, 17, tzinfo=timezone.utc)
    assert journal.local_today([e], now).isoformat() == "2026-11-17"
    assert journal.local_today([], now).isoformat() == "2026-11-18"


@needs_db
def test_an_evening_reading_keeps_its_local_date_in_the_journal(key):
    from ootk import db
    c = TestClient(app_module.app)
    r = c.post("/generate_report", data={"spread_key": "3", "seed": "100020", "topic": "Evening?",
                                         "mapping_system": "thoth", "framework": "auto", "draw_mode": "seed",
                                         "tz": "America/Vancouver"}, follow_redirects=False)
    link = r.headers["location"].rsplit("/", 1)[1]
    with db.get_db_connection() as conn:
        conn.execute("UPDATE tarot_sessions SET created_at = '2026-11-18T01:17:00Z' "
                     "WHERE report_settings->>'link' = %s;", (link,))
        conn.commit()
    entry_url = c.post("/journal/start", data={"link": link}, follow_redirects=False).headers["location"].split("?")[0]
    assert "17 Nov 2026" in c.get(entry_url).text
    assert "17 Nov 2026" in c.get("/journal").text and "18 Nov 2026" not in c.get("/journal").text
    assert "drawn 17 Nov 2026" in c.get("/journal/timeline").text
    c.post("/journal/delete")


def test_dates_in_prose_keep_a_written_year_and_look_ahead_from_the_draw():
    """The finder for answers without a Timeline list: a year written after a date is used;
    without one, the range is the next that hasn't ended by the draw, across New Year too."""
    nov17, f = date(2026, 11, 17), journal.find_windows
    assert f("The agreement comes 2 to 12 November 2027.", nov17) == [
        ("The agreement comes", date(2027, 11, 2), date(2027, 11, 12))]
    assert f("Look for it Nov 2 to Nov 12, 2027.", nov17) == [("Look for it", date(2027, 11, 2), date(2027, 11, 12))]
    assert f("Works builds December 31, 2026 to January 10, 2027.", nov17) == [
        ("Works builds", date(2026, 12, 31), date(2027, 1, 10))]
    assert f("It builds 31 December 2026 to 10 January 2027.", nov17) == [
        ("It builds", date(2026, 12, 31), date(2027, 1, 10))]
    assert f("Hastings: Oct 14 to Oct 15, 1066.", nov17) == []                    # history, not timing
    # New Year: the window running at the draw, or just ending, not next winter's.
    assert f("Works Dec 31 to Jan 9.", date(2027, 1, 5)) == [("Works", date(2026, 12, 31), date(2027, 1, 9))]
    assert f("Change runs Dec 21 to Dec 31.", date(2027, 1, 1)) == [("Change", date(2026, 12, 21), date(2026, 12, 31))]
    assert f("Expect news around 3-9 Jan.", date(2026, 12, 31)) == [("Expect news", date(2027, 1, 3), date(2027, 1, 9))]
    # A range already over at the draw is next year's, as a reading looks ahead.
    assert f("Truce Oct 13 to Oct 23.", date(2026, 11, 30)) == [("Truce", date(2027, 10, 13), date(2027, 10, 23))]


def test_everyday_words_and_other_ways_of_writing_a_range():
    nov17, f = date(2026, 11, 17), journal.find_windows
    # "may" and "march" are words, not months, without a capital M.
    assert f("Things may 2-3 weeks settle. You march 3 to 4 steps on. Maybe 3-4 mar.", nov17) == []
    assert f("May 2 to May 12 looks good.", nov17) == [("Window", date(2027, 5, 2), date(2027, 5, 12))]
    # An arrow between the dates, in prose or in the Timeline list.
    assert f("Swiftness Nov 22 → Dec 2", nov17) == [("Swiftness", date(2026, 11, 22), date(2026, 12, 2))]
    assert f("## Timeline\n- Strength: 2026-12-02 → 2026-12-12", nov17) == [
        ("Strength", date(2026, 12, 2), date(2026, 12, 12))]
    # Two ranges on one line: each is named by its own words.
    assert f("Swiftness Nov 22 to Dec 2 and then Strength Dec 2 to Dec 12.", nov17) == [
        ("Swiftness", date(2026, 11, 22), date(2026, 12, 2)), ("Strength", date(2026, 12, 2), date(2026, 12, 12))]


def test_card_windows_start_a_running_decan_at_the_draw():
    """As in the prompt's Timeline rule: a decan the Sun is already in runs from the draw."""
    from datetime import datetime, timezone
    drawn = datetime(2026, 11, 17, 21, 51, tzinfo=timezone.utc)      # the Sun in 7 of Cups' decan
    assert journal.card_windows(["7 of Cups - Debauch", "8 of Wands - Swiftness"], drawn) == [
        ("7 of Cups decan", date(2026, 11, 17), date(2026, 11, 22)),
        ("8 of Wands decan", date(2026, 11, 22), date(2026, 12, 2))]


@needs_db
def test_find_dates_offers_the_book_t_timing_card_first_and_ticked(key):
    c = TestClient(app_module.app)
    r = c.post("/generate_report", data={"spread_key": "13", "seed": "12345", "topic": "When?",
                                         "mapping_system": "thoth", "framework": "auto", "draw_mode": "seed",
                                         "significator": "Queen of Cups"}, follow_redirects=False)
    link = r.headers["location"].rsplit("/", 1)[1]
    timing = app_module.saved_reading_parts(link)[2]["timing"]
    card = timing["title"].partition(" - ")[0]
    # The prompt's Timeline rule gives the AI these very dates.
    assert f"`- the matter turns: {timing['start']} to {timing['end']}`" in c.get(f"/report/{link}").text
    entry_url = c.post("/journal/start", data={"link": link}, follow_redirects=False).headers["location"].split("?")[0]
    page = c.get(entry_url + "?find=1").text
    assert f"Book T times this reading by the {card}:" in page
    rows = [r for r in page.split("<tr") if 'name="w_label"' in r]
    found = [r for r in rows if 'class="j-found"' in r]
    first = found[0]                    # nothing saved yet: the timing card's row comes first
    assert f'value="Book T timing: {card}"' in first and " checked " in first
    assert f'value="{timing["start"]}"' in first and f'value="{timing["end"]}"' in first
    assert all(" checked " not in r for r in found[1:])                # the other cards, unticked
    # Once the answer gives those days, its own (ticked) line stands for them: no second row.
    answer = f"## Timeline\n- the matter turns: {timing['start']} to {timing['end']}"
    c.post(entry_url, data={"answer": answer, "windows_shown": "0"})
    page = c.get(entry_url + "?find=1").text
    assert f"Book T timing: {card}" not in page and f"Book T times this reading by the {card}:" in page
    c.post("/journal/delete")


def test_timeline_dates_show_both_years_and_say_when_a_bar_is_cut():
    from datetime import datetime, timezone
    def e(i, day):
        return {"entry_id": i, "thread_id": None, "drawn_at": datetime(*day, 12, tzinfo=timezone.utc), "link": "x",
                "question": "q", "spread_key": "3", "card_titles": ["a"], "answer_ai": ""}
    windows = [{"entry_id": 1, "label": "Works", "starts": date(2026, 12, 31), "ends": date(2027, 1, 10)},
               {"entry_id": 1, "label": "Near", "starts": date(2026, 12, 2), "ends": date(2026, 12, 12)},
               {"entry_id": 2, "label": "Far", "starts": date(2031, 10, 1), "ends": date(2031, 12, 10)}]
    t = journal.build_timeline([], [e(1, (2026, 11, 17)), e(2, (2026, 11, 20))], windows, date(2026, 11, 24))
    rows = {r["label"]: r for g in t["groups"] for r in g["rows"]}
    assert rows["Works"]["when"] == "31 Dec 2026 to 10 Jan 2027"          # both years across New Year
    assert rows["Near"]["when"] == "2 Dec to 12 Dec 2026" and not rows["Near"]["cut"]
    # Five years from Nov 2026 end on 1 Nov 2031: the bar stops at the edge and says it runs on.
    assert t["end"] == date(2031, 11, 1) and rows["Far"]["cut_right"] and not rows["Far"]["cut_left"]
    assert rows["Far"]["cut"] == "Runs past the end of this timeline." and rows["Far"]["when"] == "1 Oct to 10 Dec 2031"


def test_a_dated_note_below_a_marked_timeline_list_is_not_one_of_its_lines():
    nov17 = date(2026, 11, 17)
    assert journal.find_windows("## Timeline\n- a: 2027-07-02 to 2027-07-12\n\nNote: also 2027-09-01 matters", nov17) == [
        ("A", date(2027, 7, 2), date(2027, 7, 12))]
    # Items still count across blank lines, and a plain pasted list has no marks to go by.
    assert len(journal.find_windows("## Timeline\n- a: 2027-07-02 to 2027-07-12\n\n- b: 2027-09-01", nov17)) == 2
    assert len(journal.find_windows("Timeline\n\na: 2027-07-02 to 2027-07-12\n\nb: 2027-09-01", nov17)) == 2
