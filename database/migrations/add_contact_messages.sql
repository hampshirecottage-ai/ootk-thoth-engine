-- Messages sent from the site's /contact form. Only the site owner reads them, on /admin/messages;
-- nothing here is ever shown on a public page. A message keeps what the visitor typed (the message,
-- and a name and reply address only if they gave them) and when it came. No IP address, cookie or
-- browser details are stored. Safe to run more than once.
CREATE TABLE IF NOT EXISTS contact_messages (
    message_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    created_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    name character varying(60),
    reply_to character varying(200),
    body text NOT NULL CHECK (char_length(body) BETWEEN 1 AND 2000),
    is_read boolean NOT NULL DEFAULT false
);

CREATE INDEX IF NOT EXISTS idx_contact_messages_unread ON contact_messages (created_at) WHERE NOT is_read;

-- To read new messages without the admin page:
--   SELECT message_id, created_at, name, reply_to, body FROM contact_messages WHERE NOT is_read ORDER BY created_at;
-- To mark one read (use its message_id):
--   UPDATE contact_messages SET is_read = true WHERE message_id = 1;
