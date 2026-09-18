# Elixcopter

A small local app for learning French Sign Language (LSF) vocabulary using
[dico.elix-lsf.fr](https://dico.elix-lsf.fr).

## What it does

1. **Ajouter un mot** — search a French word. The app fetches the word's page
   on the Elix dictionary and shows every candidate sign video it finds (one
   per meaning/definition, sometimes several sign variants per meaning). Pick
   the correct video and save it — the app downloads the video locally and
   stores the word, its definition, and the source link as a flashcard.
2. **Réviser** — spaced-repetition review (SM-2, the algorithm behind Anki).
   Watch the sign, try to recall the word, reveal the answer, then grade
   yourself (À revoir / Difficile / Bien / Facile). Cards you get wrong come
   back sooner and more often; cards you know well are shown less and less.
3. **Mes cartes** — browse and delete saved flashcards.

## Setup

Elixcopter uses [uv](https://docs.astral.sh/uv/) for dependency management (`pyproject.toml` + `uv.lock` are checked in).

```bash
uv venv
uv sync
uv run python app.py
```

- `uv venv` creates a local `.venv/`.
- `uv sync` installs the exact locked dependencies into it.
- `uv run python app.py` runs the app inside that environment, no manual activation needed.

Then open http://localhost:5057 in your browser.

<details>
<summary>Without uv</summary>

```bash
pip install -r requirements.txt
python app.py
```

</details>

Videos are downloaded into `media/videos/`, and flashcard data lives in
`data/flashcards.db` (SQLite) — both are gitignored since they're local,
per-user data.
