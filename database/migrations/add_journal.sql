-- The private prediction journal at /admin/journal: for each real question, the reading drawn
-- for it and a hidden decoy reading drawn the same way, the two AI answers, what actually
-- happened, and a blind pick between the answers. Questions and outcomes are the site owner's
-- private notes: they are shown only behind the admin password. Safe to run more than once.
CREATE TABLE IF NOT EXISTS journal_entries (
    entry_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    created_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    question text NOT NULL CHECK (char_length(question) BETWEEN 1 AND 2000),
    settle_by date NOT NULL,
    spread_key character varying(8) NOT NULL,
    mapping_system character varying(32) NOT NULL,
    framework character varying(32) NOT NULL,
    without character varying(200) NOT NULL DEFAULT '',
    drawn_at character varying(20) NOT NULL,
    real_seed character varying(64) NOT NULL,
    decoy_seed character varying(64) NOT NULL,
    real_is_a boolean NOT NULL,
    answer_a text CHECK (char_length(answer_a) <= 60000),
    answer_b text CHECK (char_length(answer_b) <= 60000),
    outcome text CHECK (char_length(outcome) <= 10000),
    outcome_at timestamp with time zone,
    real_shown_first boolean,
    picked character varying(5) CHECK (picked IN ('real', 'decoy')),
    rating_real smallint CHECK (rating_real BETWEEN 1 AND 5),
    rating_decoy smallint CHECK (rating_decoy BETWEEN 1 AND 5),
    judged_at timestamp with time zone
);
