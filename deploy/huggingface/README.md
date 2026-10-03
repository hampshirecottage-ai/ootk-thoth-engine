---
title: OOTK Thoth Engine
emoji: 🔑
colorFrom: purple
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
short_description: Opening of the Key readings over the Thoth deck
---

# OOTK Thoth Engine

Web GUI for the Opening of the Key tarot engine. Pick a spread, draw by seed or by hand,
and read the summary-first report.

Card images are Pamela Colman Smith's 1909 Rider-Waite-Smith art, which is public domain,
shown under the Thoth titles. The Thoth paintings are copyrighted and are not included.

Readings are saved in a PostgreSQL database inside the Space, which starts empty again
whenever the Space restarts or rebuilds. To keep readings, set the `DB_HOST`, `DB_NAME`,
`DB_USER` and `DB_PASSWORD` secrets to an external PostgreSQL database; the app loads the
card tables into it on first start.
