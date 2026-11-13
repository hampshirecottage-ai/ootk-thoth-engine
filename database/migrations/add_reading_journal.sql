-- Private reading journals (/journal). A journal is opened by a secret link that only its owner
-- has; the database keeps a SHA-256 hash of that link, never the link itself. Readings stay in
-- tarot_sessions as before: an entry points at one and adds the AI's answer, notes and what
-- actually happened. Thread names, answers, notes and outcomes are encrypted by the app
-- (JOURNAL_KEY on the server) before they get here, so they read as scrambled text in the
-- console. Deleting a journal deletes its threads and entries with it. Safe to run more than once.
CREATE TABLE IF NOT EXISTS reading_journals (
    journal_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    key_hash character(64) NOT NULL UNIQUE,
    created_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_used_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reading_journal_threads (
    thread_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    journal_id bigint NOT NULL REFERENCES reading_journals (journal_id) ON DELETE CASCADE,
    name text NOT NULL CHECK (char_length(name) <= 2000),
    created_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reading_journal_entries (
    entry_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    journal_id bigint NOT NULL REFERENCES reading_journals (journal_id) ON DELETE CASCADE,
    thread_id bigint REFERENCES reading_journal_threads (thread_id) ON DELETE CASCADE,
    session_id integer NOT NULL REFERENCES tarot_sessions (session_id) ON DELETE CASCADE,
    added_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    answer text CHECK (char_length(answer) <= 300000),
    answer_ai character varying(40),
    notes text CHECK (char_length(notes) <= 20000),
    outcome text CHECK (char_length(outcome) <= 20000),
    outcome_at timestamp with time zone,
    UNIQUE (journal_id, session_id)
);

-- Timing windows on the journal's timeline: a label (encrypted, like the answer) and the days it
-- covers, e.g. "Pisces window, 19 Feb to 20 Mar", taken from the AI's answer or typed in.
CREATE TABLE IF NOT EXISTS reading_journal_windows (
    window_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entry_id bigint NOT NULL REFERENCES reading_journal_entries (entry_id) ON DELETE CASCADE,
    label text NOT NULL CHECK (char_length(label) <= 1000),
    starts date NOT NULL,
    ends date NOT NULL CHECK (ends >= starts)
);

CREATE INDEX IF NOT EXISTS idx_reading_journal_threads_journal ON reading_journal_threads (journal_id);
CREATE INDEX IF NOT EXISTS idx_reading_journal_entries_thread ON reading_journal_entries (journal_id, thread_id, added_at);
CREATE INDEX IF NOT EXISTS idx_reading_journal_windows_entry ON reading_journal_windows (entry_id);

-- How many journals and entries there are (no contents):
--   SELECT (SELECT count(*) FROM reading_journals) AS journals, (SELECT count(*) FROM reading_journal_entries) AS entries;
