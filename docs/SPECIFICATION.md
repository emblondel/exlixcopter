# Elixcopter — Functional Specification

> **Status:** Draft for review
> **Derived from:** the current reference implementation (web app + local server) in this repository
> **Scope:** full functional behaviour. Technology‑agnostic: no language, framework or library is assumed. Where a concrete value matters for behaviour (a URL pattern, a number in the scheduling algorithm, a label shown to the user), it is stated exactly.

---

## Table of contents

1. [Product overview](#1-product-overview)
2. [Glossary](#2-glossary)
3. [Personas & context of use](#3-personas--context-of-use)
4. [Feature map](#4-feature-map)
5. [Epic A — Navigation & shell](#5-epic-a--navigation--shell)
6. [Epic B — Look up a word in the Elix dictionary](#6-epic-b--look-up-a-word-in-the-elix-dictionary)
7. [Epic C — Look up a list of words](#7-epic-c--look-up-a-list-of-words)
8. [Epic D — Save a sign as a flashcard](#8-epic-d--save-a-sign-as-a-flashcard)
9. [Epic E — Review session (spaced repetition)](#9-epic-e--review-session-spaced-repetition)
10. [Epic F — Browse & manage my cards](#10-epic-f--browse--manage-my-cards)
11. [Epic G — Back up my data](#11-epic-g--back-up-my-data)
12. [Epic H — Upgrading data from an earlier version](#12-epic-h--upgrading-data-from-an-earlier-version)
13. [Domain model](#13-domain-model)
14. [Scheduling algorithm (SM‑2 variant)](#14-scheduling-algorithm-sm2-variant)
15. [Proficiency classification](#15-proficiency-classification)
16. [External source: Elix dictionary extraction rules](#16-external-source-elix-dictionary-extraction-rules)
17. [Service interface (functional contract)](#17-service-interface-functional-contract)
18. [Local storage of data & media](#18-local-storage-of-data--media)
19. [UI text catalogue (French)](#19-ui-text-catalogue-french)
20. [Non‑functional requirements](#20-non-functional-requirements)
21. [Observed gaps, quirks & open questions](#21-observed-gaps-quirks--open-questions)

---

## 1. Product overview

**Elixcopter** is a personal, locally run study tool for learning **French Sign Language (LSF)** vocabulary.

It uses the public online LSF dictionary **Elix** (`https://dico.elix-lsf.fr`) as its content source. The learner:

1. **Looks up** a French word (or a list of words). The app fetches the word's page on Elix and shows every sign video found, grouped by meaning (definition), sometimes with several sign variants per meaning.
2. **Picks** the correct sign video for the meaning they want to learn and **saves** it. The video is downloaded and kept locally, together with the word, its part of speech, its definition and a link back to the source, as a **flashcard**.
3. **Reviews** flashcards with a **spaced‑repetition** scheduler (an SM‑2 variant, the algorithm family used by Anki/SuperMemo), in two independent directions:
   - **Video → Word** (*recognize*): watch the sign, recall the word.
   - **Word → Sign** (*produce*): read the word, perform the sign, then check against the video.
4. **Manages** the deck (browse, see per‑direction proficiency, delete).
5. **Backs up** all data (cards, learning progress, and videos) as a single downloadable archive.

The user interface is in **French**. It is a single‑user application with no accounts or authentication; all data stays on the user's machine.

---

## 2. Glossary

| Term | Meaning |
|---|---|
| **Elix** | The online LSF dictionary at `https://dico.elix-lsf.fr`, the only content source. |
| **Word** | A French headword (e.g. *crier*). |
| **Part of speech (POS)** | Grammatical category as abbreviated by Elix (e.g. `v.`, `n.`, `adj.`). |
| **Meaning** | One definition of a word on Elix. A word can have several meanings; each meaning can have one or more sign videos. |
| **Variant** | One of several sign videos for the same meaning. |
| **Candidate** | A (meaning, video) pair shown in search results that the user can save. |
| **Flashcard / Card** | A saved candidate: word + POS + definition + source link + locally stored video. |
| **Mode / Direction** | One of the two review directions: `recognize` (Video → Word) or `produce` (Word → Sign). |
| **Progress** | The spaced‑repetition state of a card *for one mode*. Each card has exactly one progress record per mode. |
| **Due** | A progress record is due when its next‑review time is now or in the past. |
| **Grade** | The learner's self‑assessment after revealing an answer: `again`, `hard`, `good`, `easy`. |
| **Lapse** | A review graded `again` (i.e. a failure). |
| **Ease factor** | SM‑2 multiplier controlling how fast intervals grow. |
| **Proficiency** | A coarse label (`new`, `learning`, `weak`, `strong`) derived from progress, shown to the user. |
| **Session** | A run of consecutive reviews in one mode, optionally limited to N cards. |
| **Word list** | A batch of words looked up one after another (Epic C). |

---

## 3. Personas & context of use

**Primary persona — the LSF learner.**
A French speaker learning LSF on their own or alongside a course. Wants to build a personal vocabulary deck from a trusted dictionary, and to practise both understanding signs and producing them. Runs the app on their own computer and opens it in a web browser.

Context assumptions:
- Single user, single machine; no login.
- Internet access is needed to look up words and download videos; reviewing and browsing work from locally stored data and videos.
- The user may want to move their deck to another machine or keep a safety copy (hence backup).

---

## 4. Feature map

| Epic | Feature | Tab (UI) |
|---|---|---|
| A | Tabbed navigation | all |
| B | Single‑word lookup, suggestions on no match, "already saved" detection | **Ajouter un mot** |
| C | Word‑list lookup with previous/next navigation | **Ajouter un mot** |
| D | Save a candidate as a flashcard (with local video download) | **Ajouter un mot** |
| E | Review sessions in two modes, configurable size, SM‑2 grading, proficiency legend | **Réviser** |
| F | Deck listing, statistics per mode, delete | **Mes cartes** |
| G | One‑click backup archive | **Mes cartes** |
| H | Automatic upgrade of data created by an earlier single‑direction version | (transparent) |

---

## 5. Epic A — Navigation & shell

### US‑A1 — Switch between the three areas
> *As a learner, I want three clearly separated areas — add words, review, my cards — so that I can focus on one activity at a time.*

**Acceptance criteria**
- The header shows the brand (✋ **Elixcopter**) and three tabs, in this order: **Ajouter un mot**, **Réviser**, **Mes cartes**.
- **Ajouter un mot** is active on first load.
- Exactly one tab panel is visible at a time; the active tab button is visually highlighted.
- Activating **Réviser** always returns the review area to its **session setup** screen (any in‑progress session view is abandoned; already‑submitted grades are kept).
- Activating **Mes cartes** always reloads the deck from storage (so it reflects cards saved in the meantime).
- Activating **Ajouter un mot** keeps whatever search state was present.
- The page title is "Elixcopter — Apprendre la LSF"; the document language is French.

---

## 6. Epic B — Look up a word in the Elix dictionary

### US‑B1 — Search a word
> *As a learner, I want to type a French word and see all the LSF sign videos Elix has for it, so that I can choose which one to learn.*

**Acceptance criteria**
- A text field (placeholder: "Chercher un mot (ex : crier)") and a **Chercher** button. Submitting with Enter or the button triggers the search. An empty field cannot be submitted.
- Leading/trailing whitespace is trimmed. An empty query is rejected (service returns *missing query* error).
- While searching, the status line shows "Recherche en cours…", and previous suggestions/results are cleared.
- The app fetches the word's Elix page (see [§16](#16-external-source-elix-dictionary-extraction-rules)) and extracts the list of meanings with their videos.
- On success with ≥1 meaning, the status line reads:
  `{N} vidéo(s) trouvée(s) pour « {query} ». Choisissez le bon signe pour chaque sens.`
  where **N is the number of meanings** (not the number of videos — see [§21](#21-observed-gaps-quirks--open-questions)).
- Results are shown as a grid of **candidate cards**, one per (meaning, video) pair, in source order (meanings in page order, variants in page order within a meaning).

### US‑B2 — Understand each candidate
> *As a learner, I want each candidate to show its meaning and grammatical category, so that I can pick the sign that matches the sense I intend.*

Each candidate card shows:
- The **part of speech** (may be blank).
- The **sign video**, streamed directly from Elix, with playback controls, loading only metadata until played.
- The **definition** text of the meaning.
- If the meaning has more than one video: a label **"Variante {i}/{n}"** (1‑based). Otherwise nothing.
- An action (see US‑D1 / US‑B4).

### US‑B3 — Get suggestions when there is no exact match
> *As a learner, if my word is not found, I want Elix's suggestions so I can find the right entry quickly.*

**Acceptance criteria**
- If no meaning with at least one video is found, the status line reads `Aucun résultat exact pour « {query} ». Suggestions :`
- Below it, each suggestion is a clickable button. Clicking one runs a new search for that suggestion (and puts it in the search field).
- Suggestions are taken from Elix's own suggestion block, de‑duplicated (order preserved) and **capped at 20**.
- Suggestions are only computed/displayed when there are no meanings.
- If Elix returns no suggestions either, the status line is shown with an empty suggestion list.

### US‑B4 — See which candidates I already saved
> *As a learner, I want to know which videos are already in my deck, so that I don't save duplicates and can jump to them.*

**Acceptance criteria**
- For every video URL in the results, the app checks whether a card already exists with that **exact source video URL**.
- An already‑saved candidate is visually marked (distinct style) and shows a badge **"✔ Déjà enregistrée"** next to its POS.
- Instead of the save button it shows **"Voir dans Mes cartes"**, which switches to the **Mes cartes** tab.

### US‑B5 — Be told when the lookup fails
> *As a learner, I want a clear error if the dictionary can't be reached.*

**Acceptance criteria**
- Any failure fetching or reading the Elix page (network error, timeout, non‑success HTTP status) is reported as a lookup failure (*bad gateway* category) with the error message.
- The status line shows the error message, styled as an error.
- Timeout for fetching a word page: **15 s**.

---

## 7. Epic C — Look up a list of words

### US‑C1 — Enter a list of words
> *As a learner with a vocabulary list from class, I want to paste it once and go through each word in turn.*

**Acceptance criteria**
- Below the search form, a link‑style button **"📋 Chercher une liste de mots"**.
- Clicking it hides the single‑word form and this button, and shows a list panel:
  - Label: "Liste de mots (un par ligne, ou séparés par des virgules)"
  - A multi‑line text area (placeholder showing one word per line), focused automatically.
  - **Commencer** and **Annuler** buttons.
- **Annuler** hides the list panel and restores the single‑word form and the list button (text is kept).
- **Commencer** parses the input:
  - split on **newlines and commas**;
  - trim each item; **lower‑case** each item;
  - drop empty items;
  - **de‑duplicate**, keeping first occurrence order.
- If the parsed list is empty, nothing happens.
- Otherwise the list panel is hidden and a **queue bar** appears; the first word is searched immediately.

### US‑C2 — Walk through the list
> *As a learner, I want to move forward and back through my list and see where I am.*

**Acceptance criteria**
- The queue bar shows:
  - a progress badge `{position} / {total}` (1‑based);
  - the current word;
  - **◀ Précédent**, **Suivant ▶** and **Quitter la liste** buttons.
- Moving to a position runs a normal search (Epic B) for that word, which also fills the search field; all behaviours of Epic B and D (saving, suggestions, already‑saved) apply.
- **Précédent** is disabled on the first word.
- On the last word, the next button reads **"Terminer ✔"**; pressing it ends the list with the status message **"Liste terminée 🎉"**.
- **Quitter la liste** ends the list with no message.
- Ending the list (either way): hides the queue bar, restores the single‑word form and list button, clears the list text area, clears suggestions and results, and resets the status line (non‑error).
- Clicking a suggestion while in list mode searches that suggestion but does **not** change the list position.

---

## 8. Epic D — Save a sign as a flashcard

### US‑D1 — Save the right sign
> *As a learner, when I recognise the sign that matches the meaning I want, I want to save it as a flashcard in one click.*

**Acceptance criteria**
- Each not‑yet‑saved candidate has a button **"✔ C'est le bon signe — enregistrer"**.
- On click: the button is disabled and reads **"Enregistrement…"**.
- The card is created with:
  - **word** — the headword as written in the Elix entry title (not necessarily the user's query);
  - **part of speech**, **definition**, **source URL** of the meaning;
  - **source video URL** of the chosen candidate.
- Required: word and video URL (non‑empty after trimming); otherwise *invalid request*.
- The video is **downloaded from Elix and stored locally** before the card is recorded (timeout **30 s**). If the download fails, no card is created.
- The new card is initialised with **one progress record per mode** (`recognize`, `produce`), each with default SM‑2 state and **due immediately** (due = creation time). Thus a new card is available for review in both directions straight away.
- On success: the button reads **"✔ Enregistré dans les cartes"** (stays disabled) and the candidate gets the "saved" visual style.
- On failure: the button is re‑enabled and reads **"Erreur — réessayer"**.

### US‑D2 — Prevent duplicate cards
> *As a learner, I don't want the same video saved twice.*

**Acceptance criteria**
- Uniqueness is on the **source video URL**. If a card with that URL already exists, the save is refused (*conflict*) with the message "This video is already saved as a flashcard" and the existing card id. No download happens.
- The same word **may** have several cards (different meanings or variants).

### US‑D3 — Keep the video available offline
- The locally stored file is named `{slug}-{k}.mp4` where:
  - **slug** = the word transliterated to ASCII (accents removed), every run of non‑alphanumeric characters replaced by `-`, leading/trailing `-` removed, lower‑cased; `mot` if the result is empty;
  - **k** = (number of existing cards with exactly the same word) + 1.
- All subsequent playback (review and deck) uses the local copy, not Elix.

---

## 9. Epic E — Review session (spaced repetition)

### US‑E1 — Configure a session
> *As a learner, I want to choose the direction and how many cards I'll review, so that sessions fit my time.*

**Session setup screen** ("Nouvelle session"):
- **Mode** (radio, default **Vidéo → Mot**):
  - **Vidéo → Mot** — "Regardez le signe, devinez le mot." (`recognize`)
  - **Mot → Signe** — "Lisez le mot, essayez de faire le signe, puis vérifiez." (`produce`)
- **Nombre de cartes** (select): **10** (default), **20**, **30**, **Toutes les cartes dues** (no limit).
- **Commencer** starts the session with a reviewed counter at 0.
- A collapsible legend "ℹ️ Que signifient les statuts des cartes ?" explains proficiency labels (text in [§19](#19-ui-text-catalogue-french)).

### US‑E2 — Get the next card to review
> *As a learner, I want the most overdue card first.*

**Acceptance criteria**
- The next card is the card whose progress **for the selected mode** is due (due time ≤ now) with the **earliest due time**.
- Only that mode's progress is considered/returned; the other mode is unaffected.
- If no card is due:
  - if the session has already reviewed ≥1 card → **session complete** screen: `Session terminée — {n} carte(s) revue(s), plus aucune carte due 🎉`;
  - otherwise → **empty** screen: "Aucune carte à réviser pour le moment 🎉" plus either
    - `Prochaine carte due le {date/time in French locale}.` (the earliest future due time for this mode), or
    - "Ajoutez des mots dans l'onglet « Ajouter un mot » pour commencer." when there are no cards at all;
    - with a **Retour** button back to setup.
- If the session has a limit and the reviewed count has reached it → **session complete**: `Session terminée — {n} carte(s) revue(s) 🎉`, with a **Nouvelle session** button back to setup.

### US‑E3 — Review in "Video → Word" mode
> *As a learner, I want to watch a sign and try to recall the French word.*

- **Prompt:** the card's local video only, auto‑playing, muted, with controls, inline. Word and definition hidden.
- Button **"Afficher la réponse"**.
- **Reveal:** shows the word and definition (video stays visible), hides the reveal button, shows the grade buttons.

### US‑E4 — Review in "Word → Sign" mode
> *As a learner, I want to read the word and try to produce the sign, then check myself against the video.*

- **Prompt:** the word **and** its definition (the definition disambiguates homonyms), plus a placeholder (🤟 "Essayez de faire le signe, puis révélez la vidéo pour vérifier."). The video is **not loaded** until reveal, so it cannot play or be heard behind the placeholder.
- Button **"Afficher la vidéo"**.
- **Reveal:** hides the placeholder, loads and shows the video, shows grade buttons.
- The card has a distinct visual style in this mode.

### US‑E5 — Session context while reviewing
Each card shows badges:
- **Session progress:** `{reviewed+1} / {limit}` or, with no limit, `{reviewed+1}`.
- **Part of speech** (may be blank).
- **Proficiency** for this mode, with its French label and colour (see [§15](#15-proficiency-classification)).

### US‑E6 — Grade myself
> *As a learner, I want to say how well I knew the card, so that it comes back at the right time.*

**Acceptance criteria**
- Four buttons, shown only after reveal: **À revoir** (`again`), **Difficile** (`hard`), **Bien** (`good`), **Facile** (`easy`).
- Clicking one submits the grade for this card **and this mode**, recomputes its schedule ([§14](#14-scheduling-algorithm-sm2-variant)), increments the session's reviewed count and loads the next card.
- While a grade is being submitted, further grade clicks are ignored (no double submission); buttons look disabled.
- Invalid grade or mode → *invalid request*; unknown card/mode → *not found*.
- A card graded `again` becomes due again after ~1 hour, so it typically does **not** reappear immediately in the same session.

### US‑E7 — Independent progress per direction
> *As a learner, knowing a sign one way doesn't mean I know it the other way; I want each direction tracked separately.*

- Grading in one mode changes **only** that mode's progress for the card.
- Proficiency, due dates and statistics are always per mode.

---

## 10. Epic F — Browse & manage my cards

### US‑F1 — See my deck
> *As a learner, I want to see all my cards with their status in each direction.*

**Acceptance criteria**
- While loading: "Chargement…".
- Cards are listed **newest first** (by creation time).
- Each deck card shows: the local video (controls, metadata preload), the word as a title, the definition, and for each mode (**Vidéo → Mot**, **Mot → Signe**) a proficiency badge.
- If there are no cards: "Aucune carte pour le moment."

### US‑F2 — See my deck statistics
- A toolbar above the list shows:
  - total: `{N}` "carte(s) au total";
  - for each mode, a group titled with the mode label containing four counters in order **Nouveau, En cours, Fragile, Acquis** — the number of cards whose progress in that mode has that proficiency.

### US‑F3 — Delete a card
> *As a learner, I want to remove a card I saved by mistake.*

**Acceptance criteria**
- Each deck card has a **Supprimer** button.
- A confirmation dialog asks `Supprimer la carte « {word} » ?`. Cancelling does nothing.
- On confirm: the card **and both progress records** are deleted and its **local video file is removed** (if present). The deck reloads.
- Deleting an unknown card → *not found*.
- Once deleted, the video becomes saveable again from search results.

---

## 11. Epic G — Back up my data

### US‑G1 — Download a full backup
> *As a learner, I want a single file containing my whole deck and progress, so I can keep it safe or move it to another computer.*

**Acceptance criteria**
- In **Mes cartes**, a button **"⬇ Télécharger une sauvegarde"** triggers a download.
- The download is a **ZIP archive** named `elixcopter-backup-YYYYMMDD-HHMMSS.zip` (UTC timestamp).
- Contents:
  - `data/flashcards.db` — a **consistent snapshot** of the card/progress store (taken in a way that cannot capture a half‑written state if a write happens concurrently); omitted if the store does not exist yet;
  - `media/videos/*.mp4` — every locally stored video, in name order.
- The archive layout mirrors the local data layout, so restoring = extracting it into the app's directory (there is **no in‑app restore**; see [§21](#21-observed-gaps-quirks--open-questions)).

---

## 12. Epic H — Upgrading data from an earlier version

### US‑H1 — Keep my history when the app gains two‑direction review
> *As an existing user, upgrading must not lose my learning history.*

Earlier versions stored a **single** SM‑2 state directly on each card (only the Video → Word direction existed). On start‑up, if such legacy data is detected (the card record still carries scheduling fields), it is migrated automatically and once:
- Card identity and content (id, word, POS, definition, source URL, video URL, video file, creation time) are preserved.
- The legacy scheduling state becomes the card's **`recognize`** progress (ease, interval, repetitions, lapses, due, last reviewed).
- A fresh **`produce`** progress is created: default state, due at the card's creation time (i.e. immediately due), never reviewed.
- After migration the data is in the current model; the migration does not run again.
- On start‑up the store and the media folder are created if missing.

---

## 13. Domain model

### 13.1 Card
| Field | Type | Required | Notes |
|---|---|---|---|
| id | integer, auto | yes | Never reused. |
| word | text | yes | Headword from Elix title. |
| part_of_speech | text | no | e.g. `v.` |
| definition | text | no | Meaning heading text. |
| source_url | text | no | Link to the meaning on Elix (falls back to the word page). |
| video_url | text | yes | Original Elix video URL; **unique across cards** (enforced by the save operation). |
| video_path | text | yes | Relative path of local file, `videos/{file}.mp4`. |
| created_at | timestamp (UTC, ISO‑8601) | yes | |

### 13.2 Progress (one per card per mode)
| Field | Type | Default | Notes |
|---|---|---|---|
| card_id | ref → Card | — | Deleted with the card. |
| mode | `recognize` \| `produce` | — | (card_id, mode) is unique. |
| ease_factor | decimal | 2.5 | ≥ 1.3 |
| interval_days | decimal | 0 | Fractional days allowed. |
| repetitions | integer | 0 | Consecutive successful reviews. |
| lapses | integer | 0 | Total `again` grades, never reset. |
| due_at | timestamp (UTC) | creation time | |
| last_reviewed_at | timestamp (UTC) | none | |

### 13.3 Derived values
- **proficiency** (per progress record) — [§15](#15-proficiency-classification).
- **video_src** — the local URL at which the card's video is served (`/media/{video_path}`).

### 13.4 Lifecycle
```
(search candidate) --save--> Card + Progress[recognize] + Progress[produce] (all due now)
Progress --grade--> Progress (rescheduled)
Card --delete--> (card, its progress records and its video file removed)
```

---

## 14. Scheduling algorithm (SM‑2 variant)

Input: grade, current ease factor (EF), interval (I, days), repetitions (R). Output: new EF, I, R, due time, last‑reviewed time, and whether this was a lapse.

**Grade → quality (q)**

| Grade | UI label | q |
|---|---|---|
| again | À revoir | 1 |
| hard | Difficile | 3 |
| good | Bien | 4 |
| easy | Facile | 5 |

**Interval & repetitions**
- If **q < 3** (i.e. `again`) — *lapse*:
  `R ← 0`, `I ← 1/24 day (≈ 1 hour)`, `lapses ← lapses + 1`.
- Else (hard/good/easy) — *success*:
  - if R = 0 → `I ← 1`
  - if R = 1 → `I ← 6`
  - else → `I ← round(I × EF, 2)` (using the EF **before** this review's update)
  - then `R ← R + 1`.

**Ease factor** (applied for every grade, including lapses)
`EF ← max(1.3, round(EF + (0.1 − (5 − q) × (0.08 + (5 − q) × 0.02)), 2))`

Resulting EF change: again −0.54, hard −0.14, good ±0, easy +0.10.

**Timestamps**
`due_at ← now + I days`; `last_reviewed_at ← now` (UTC).

**Worked example** (new card, repeatedly graded `good`): I = 1 d → 6 d → 15 d → 37.5 d …, EF stays 2.5.

---

## 15. Proficiency classification

Evaluated per progress record, first matching rule wins:

| Order | Condition | Label (code) | UI label |
|---|---|---|---|
| 1 | repetitions = 0 | `new` | **Nouveau** |
| 2 | lapses ≥ 2 **or** ease ≤ 1.8 | `weak` | **Fragile** |
| 3 | ease ≥ 2.4 **and** repetitions ≥ 3 | `strong` | **Acquis** |
| 4 | otherwise | `learning` | **En cours** |

Note: a card just graded `again` has repetitions 0 and therefore shows as **Nouveau** until it is successfully reviewed again, even if it has many lapses.

Each label has its own colour, used consistently on review badges, deck badges and statistics counters.

---

## 16. External source: Elix dictionary extraction rules

The integration is read‑only and identifies itself as `Elixcopter/1.0 (personal LSF flashcard study tool)`.

**Word page address**: `https://dico.elix-lsf.fr/dictionnaire/{url‑encoded word}`.

Elix serves all necessary content in the page itself (no client‑side rendering required). Extraction rules:

1. The page contains one or more **word sections**. Each has a **title** like `crier (v.)`.
   - **headword** = text before the last `(`, trimmed (or the whole title if there is none);
   - **part of speech** = text after the last `(`, with `)` removed, trimmed.
   - Sections without a title are ignored.
2. Each word section contains **meaning blocks**. For each:
   - **definition** = the meaning's heading text (empty if absent);
   - **source URL** = the meaning's "source" link if present, else the word page URL;
   - **video URLs** = every video in the meaning's video area, resolved to absolute URLs against the Elix base URL, in page order.
   - Meaning blocks with **no video** are skipped.
3. If no meaning was retained, **suggestions** = text of each link in the page's suggestions block whose target is a dictionary entry (`/dictionnaire/…`), non‑empty, de‑duplicated preserving order, max 20.

**Lookup result** (functional shape):
```
{ word: <the user's query>, url: <word page URL>,
  meanings: [ { word, part_of_speech, definition, source_url, video_urls[] } ],
  suggestions: [ text ],
  saved: { <video_url>: <card id> }   // only URLs already saved
}
```

**Video download**: plain fetch of the video URL, streamed to the local file; timeout 30 s; failure aborts card creation.

---

## 17. Service interface (functional contract)

The reference implementation splits a browser UI from a local service. Any implementation must offer equivalent operations; the HTTP form is given for reference.

| # | Operation | Reference form | Input | Success | Errors |
|---|---|---|---|---|---|
| 1 | Look up word | `GET /api/search?q=` | query | Lookup result (§16) | 400 missing query; 502 lookup failure |
| 2 | Create card | `POST /api/cards` | word*, video_url*, definition, part_of_speech, source_url | 201 Deck card | 400 missing fields; 409 duplicate video (+ existing id) |
| 3 | List cards | `GET /api/cards` | — | Deck cards, newest first | — |
| 4 | Delete card | `DELETE /api/cards/{id}` | id | `{ok: true}` | 404 |
| 5 | Next due card | `GET /api/review/next?mode=` | mode (default `recognize`) | `{card: Review card, next_due_at: null}` or `{card: null, next_due_at: <earliest due time or null>}` | 400 invalid mode |
| 6 | Submit grade | `POST /api/review/{id}` | grade*, mode (default `recognize`) | Updated Review card | 400 invalid grade/mode; 404 |
| 7 | Serve media | `GET /media/{path}` | path | video file | 404 |
| 8 | Backup | `GET /api/backup` | — | ZIP attachment (§11) | — |
| 9 | UI | `GET /` | — | application page | — |

**Deck card** = all Card fields + `video_src` + `progress: { recognize: {...}, produce: {...} }`, each with ease_factor, interval_days, repetitions, lapses, due_at, last_reviewed_at, proficiency.

**Review card** = all Card fields + `video_src` + the selected mode's progress fields flattened (ease_factor, interval_days, repetitions, lapses, due_at, last_reviewed_at) + `proficiency`.

Note on "next due card" when nothing is due: `next_due_at` is the earliest due time among **all** progress records of that mode — which, when nothing is due, is necessarily in the future — or null when there are no cards.

---

## 18. Local storage of data & media

- All persistent data lives in the application's directory:
  - `data/flashcards.db` — cards and progress;
  - `media/videos/` — downloaded videos (`.mp4`).
- Both are per‑user and excluded from version control.
- Deleting a card cascades to its progress records.
- The service runs locally (reference port **5057**); the user opens it in a browser at `http://localhost:5057`.

---

## 19. UI text catalogue (French)

| Location | Text |
|---|---|
| Tabs | Ajouter un mot · Réviser · Mes cartes |
| Search placeholder / button | Chercher un mot (ex : crier) · Chercher |
| Searching | Recherche en cours… |
| Results | {N} vidéo(s) trouvée(s) pour « {mot} ». Choisissez le bon signe pour chaque sens. |
| No match | Aucun résultat exact pour « {mot} ». Suggestions : |
| Variant | Variante {i}/{n} |
| Save button states | ✔ C'est le bon signe — enregistrer · Enregistrement… · ✔ Enregistré dans les cartes · Erreur — réessayer |
| Already saved | ✔ Déjà enregistrée · Voir dans Mes cartes |
| List mode | 📋 Chercher une liste de mots · Liste de mots (un par ligne, ou séparés par des virgules) · Commencer · Annuler |
| List navigation | ◀ Précédent · Suivant ▶ · Terminer ✔ · Quitter la liste · Liste terminée 🎉 |
| Review setup | Nouvelle session · Mode · Vidéo → Mot (Regardez le signe, devinez le mot.) · Mot → Signe (Lisez le mot, essayez de faire le signe, puis vérifiez.) · Nombre de cartes · 10/20/30/Toutes les cartes dues · Commencer |
| Review | Afficher la réponse · Afficher la vidéo · Essayez de faire le signe, puis révélez la vidéo pour vérifier. |
| Grades | À revoir · Difficile · Bien · Facile |
| Empty | Aucune carte à réviser pour le moment 🎉 · Prochaine carte due le {date}. · Ajoutez des mots dans l'onglet « Ajouter un mot » pour commencer. · Retour |
| Session end | Session terminée — {n} carte(s) revue(s) 🎉 · Session terminée — {n} carte(s) revue(s), plus aucune carte due 🎉 · Nouvelle session |
| Proficiency | Nouveau · En cours · Fragile · Acquis |
| Deck | Chargement… · Aucune carte pour le moment. · carte(s) au total · Supprimer · Supprimer la carte « {mot} » ? · ⬇ Télécharger une sauvegarde |

**Proficiency legend text**
- **Nouveau** — La carte n'a encore jamais été validée dans ce sens de révision : soit elle vient d'être ajoutée, soit vous avez toujours répondu « À revoir » jusqu'ici.
- **En cours** — Elle a été validée au moins une fois, sans être ni fragile ni acquise pour l'instant — c'est l'état par défaut pendant l'apprentissage.
- **Fragile** — Elle a été ratée (« À revoir ») au moins 2 fois au total, ou jugée difficile trop souvent — elle revient plus fréquemment pour être retravaillée.
- **Acquis** — Elle a été validée au moins 3 fois de suite avec de bonnes réponses — vous la connaissez bien, elle revient de moins en moins souvent.
- Footnote: Chaque sens de révision (Vidéo → Mot et Mot → Signe) a son propre statut : bien connaître un mot dans un sens ne veut pas dire le connaître dans l'autre.

---

## 20. Non‑functional requirements

| Area | Requirement |
|---|---|
| Deployment | Runs locally on the user's machine; accessed through a web browser. |
| Users | Single user, no authentication. |
| Privacy | All data and media stored locally; only outbound traffic is to Elix. |
| Offline | Review and deck browsing work without internet once videos are downloaded. Lookup and saving require internet. |
| Resilience | Backups must be internally consistent even if a write happens during export. |
| Politeness to source | Identify the client with a descriptive user agent; one page request per lookup; one download per saved card. |
| Responsiveness | Usable on desktop and mobile browser widths (responsive layout). |
| Language | UI in French. |
| Timeouts | Word lookup 15 s; video download 30 s. |

---

## 21. Observed gaps, quirks & open questions

These are behaviours of the reference implementation worth a decision before re‑implementation. They are **not** requirements unless confirmed.

1. **Result count wording** — the message says "{N} vidéo(s)" but N counts meanings, not videos. *Fix to count videos?*
2. **Echoed query vs. headword** — the results message uses the user's query, while the saved card uses the Elix headword (e.g. query "Crier" → card "crier"). *Acceptable?*
3. **Local filename collisions** — the file index is "number of cards with the same word + 1". After deleting a non‑last card of a word, the next save can reuse an existing filename and **overwrite another card's video**. *Use a collision‑free naming scheme (e.g. card id).*
4. **Partial failure on save** — if the download succeeds but recording the card fails, an orphan video file remains. Conversely, a failed download may leave a partial file.
5. **Grade submission errors are silent** — the client advances to the next card even if the grade was rejected or the request failed.
6. **"again" within a session** — failed cards return after ~1 h, so they usually do not reappear in the current session despite the "same‑day retry" intent. *Add in‑session relearning?*
7. **Proficiency after a lapse** — a lapsed card shows **Nouveau** (repetitions reset to 0) even with many lapses, which can contradict the legend's notion of "Fragile". *Evaluate `weak` before `new`?*
8. **Hard grade advances** — `hard` moves the card forward on the normal 1 → 6 → ×EF ladder (only EF drops). *Intended?*
9. **No restore** — backup exists but restore is manual (extract the archive). *Add in‑app import?*
10. **No card editing** — word/definition cannot be edited after saving; no tags, decks, search or sort in "Mes cartes".
11. **Suggestion click in list mode** — searches the suggestion without updating the list position/word display.
12. **Session counting with "all"** — progress shows only a running count; no total of due cards is shown beforehand.
13. **Concurrency** — single‑user assumption; no protection against two simultaneous saves of the same video beyond the duplicate check.
14. **Dependency on Elix markup** — extraction relies on Elix's page structure; any redesign breaks lookups. *Monitor / make extraction rules configurable?*
