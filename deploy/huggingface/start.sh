#!/bin/sh
# Container entry point: start a local PostgreSQL unless DB_HOST points at an external
# one, load database/schema.sql into an empty database, then serve the web GUI on 7860.
set -e

if [ -z "$DB_HOST" ]; then
    # Local database. Space storage is ephemeral, so it starts empty on every restart.
    export DB_HOST=/tmp DB_USER=user DB_NAME=my_tarot_db DB_PORT=5432
    if [ ! -s "$PGDATA/PG_VERSION" ]; then
        initdb -D "$PGDATA" -U user --auth=trust >/dev/null
    fi
    pg_ctl -D "$PGDATA" -l "$HOME/postgres.log" -w \
        -o "-k /tmp -c listen_addresses=''" start
    createdb -h /tmp -U user my_tarot_db 2>/dev/null || true
fi

# PGCONNECT_TIMEOUT: without it psql waits forever on a database that doesn't answer, and the
# web server below never opens its port, so the host gives up on the boot. The app itself
# uses the same limit (DB_CONNECT_TIMEOUT) and shows a "database unreachable" page instead.
export PGHOST="$DB_HOST" PGPORT="${DB_PORT:-5432}" PGUSER="${DB_USER:-postgres}" \
       PGDATABASE="${DB_NAME:-my_tarot_db}" PGPASSWORD="$DB_PASSWORD" \
       PGCONNECT_TIMEOUT="${DB_CONNECT_TIMEOUT:-10}"

if ! loaded="$(psql -tAc "SELECT to_regclass('public.thoth_cards') IS NOT NULL")"; then
    echo "Database unreachable at boot; starting the web server anyway"
elif [ "$loaded" != "t" ]; then
    echo "Loading database/schema.sql"
    psql -q -f database/schema.sql >/dev/null 2>"$HOME/schema-load.log" || true
    echo "Cards loaded: $(psql -tAc 'SELECT count(*) FROM thoth_cards')"
fi

exec uvicorn ootk.web:app --host 0.0.0.0 --port "${PORT:-7860}" --proxy-headers --forwarded-allow-ips='*' --no-server-header
