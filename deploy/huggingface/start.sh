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

export PGHOST="$DB_HOST" PGPORT="${DB_PORT:-5432}" PGUSER="${DB_USER:-postgres}" \
       PGDATABASE="${DB_NAME:-my_tarot_db}" PGPASSWORD="$DB_PASSWORD"

if [ "$(psql -tAc "SELECT to_regclass('public.thoth_cards') IS NOT NULL")" != "t" ]; then
    echo "Loading database/schema.sql"
    # The dump's ootk_admin grants fail on a fresh server; that is harmless.
    psql -q -f database/schema.sql >/dev/null 2>"$HOME/schema-load.log" || true
    echo "Cards loaded: $(psql -tAc 'SELECT count(*) FROM thoth_cards')"
fi

exec uvicorn ootk.web:app --host 0.0.0.0 --port 7860 --proxy-headers --forwarded-allow-ips='*'
