-- Testimonials sent from /testimonial, one per visitor session. The front page shows one
-- approved testimonial a day; new ones wait (approved = false) until the site owner approves them.
-- Session details are private: a random session id from the visitor's cookie, the time, the
-- browser's user agent and, only when VISITOR_HASH_KEY is set, a keyed hash of the IP address
-- (never the address itself). Safe to run more than once.
CREATE TABLE IF NOT EXISTS testimonials (
    testimonial_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    created_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    session_id character varying(64) NOT NULL UNIQUE,
    name character varying(60),
    body text NOT NULL CHECK (char_length(body) BETWEEN 1 AND 600),
    approved boolean NOT NULL DEFAULT false,
    user_agent character varying(200),
    ip_hash character(64)
);

CREATE INDEX IF NOT EXISTS idx_testimonials_approved ON testimonials (testimonial_id) WHERE approved;

-- To review new testimonials:
--   SELECT testimonial_id, created_at, name, body FROM testimonials WHERE NOT approved ORDER BY created_at;
-- To approve one (use its testimonial_id):
--   UPDATE testimonials SET approved = true WHERE testimonial_id = 1;
-- To take one down again:
--   UPDATE testimonials SET approved = false WHERE testimonial_id = 1;
