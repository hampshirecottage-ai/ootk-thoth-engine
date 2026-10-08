# Web GUI image for Hugging Face Spaces (Docker SDK) or any Docker host.
# Runs PostgreSQL and the FastAPI app in one container on port 7860.
# Card images are the public-domain 1909 Rider-Waite-Smith art (static/cards). The Thoth
# paintings are copyrighted and never go in the image.
FROM python:3.12-slim-trixie

RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face runs Space containers as uid 1000.
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/usr/lib/postgresql/17/bin:/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PGDATA=/home/user/pgdata
WORKDIR /home/user/app

COPY --chown=user pyproject.toml README.md requirements-lock.txt ./
COPY --chown=user src ./src
RUN pip install --no-cache-dir -c requirements-lock.txt -e .

COPY --chown=user templates ./templates
COPY --chown=user static/js ./static/js
COPY --chown=user static/cards ./static/cards
COPY --chown=user static/site ./static/site
COPY --chown=user static/history ./static/history
COPY --chown=user static/fonts ./static/fonts
COPY --chown=user database/schema.sql ./database/schema.sql
COPY --chown=user deploy/huggingface/start.sh ./start.sh

USER user
EXPOSE 7860
CMD ["./start.sh"]
