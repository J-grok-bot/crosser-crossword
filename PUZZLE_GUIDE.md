# Crosser puzzle guide

How puzzles are made, validated, rated, and how future generation should learn from ratings.

## Files
- `tools/puzzles_src.json` – source of truth. Each puzzle: `id, title, author, date, grid` (rows, `#` = block),
  `clues` keyed by ANSWER (or `ANSWER/a`, `ANSWER/d` if an answer is clued differently by direction),
  `phrases` (multi-word entries not in the word list), and `meta`:
  `difficulty` (easy/medium/hard), `themeType` (themeless, added-word, starts-with, hidden-word, …),
  `clueStyle` (straight, wordplay-heavy, mixed), `notes`.
  Cross-references are written `{A:ANSWER}` / `{D:ANSWER}` and resolved to numbers at build.
- `tools/build.py` – validates and writes `puzzles.js`. Run `python3 tools/build.py`; it must print `ok` for every puzzle.
- `tools/enable1.txt` – public-domain ENABLE word list used to verify every non-theme entry is a real word.

## Quality bar (published-crossword standards)
- 180° rotational symmetry, all cells checked, no 2-letter entries, connected grid.
- 15x15 themed: ≤78 words, ~36–42 blocks; 11x11: ≤44 words; minis: 5x5, 10 entries.
- Coherent theme with a revealer or a title that unlocks it.
- Fill: common, lively words; avoid crosswordese (ESNE, ALEE…), obscure abbreviations, partials, roll-your-owns, and offensive words (see `bad.txt` in the generator).
- Clues: all original; vary types (definition, fill-in-the-blank, wordplay with `?`, misdirection); never reuse a clue verbatim across puzzles.

## Ratings (in-app)
After solving (in the congrats modal) or from the archive (“Rate” link on each card) a solver gives 1–5 stars,
optional tags (`fun, great theme, clever clues, smooth fill, too easy, too hard, obscure fill, boring clues, weak theme`) and a note.
Ratings are stored in `localStorage` key `xw:ratings`. The archive's **Export ratings.json** button downloads:

```json
{ "schema": "crosser-ratings/1", "exportedAt": "...",
  "ratings": [ { "puzzleId": "...", "stars": 4, "tags": ["clever clues"], "note": "...",
                 "ratedAt": "...", "solved": true, "solveTimeSec": 312, "usedReveal": false,
                 "meta": { "title": "...", "size": "15x15", "difficulty": "medium",
                           "themeType": "starts-with", "clueStyle": "mixed", "wordCount": 76, "source": "original" } } ],
  "puzzles": [ { "id": "...", "title": "...", "size": "...", "difficulty": "...", "themeType": "...", "clueStyle": "...", "wordCount": 76 } ] }
```
Save that file as `/workspace/crossword/ratings.json` so a generator can read it.

## How future generation should use ratings
1. Load `ratings.json`; join each rating to its puzzle `meta` (and to `puzzles_src.json` for clue text).
2. Score traits. For each trait value (difficulty, themeType, clueStyle, size, wordCount bucket, each tag),
   compute a weighted mean of `(stars − 3)`, with weight 1 for each rating (recent ratings ×1.5). Shrink toward 0
   with a prior: `score = sum / (n + 2)` so one rating doesn't dominate.
3. Steer the next batch:
   - Choose size/difficulty/themeType/clueStyle in proportion to `exp(score)` (keep ≥15% exploration of other options).
   - Tags: `too easy` → raise difficulty one step (more misdirection/`?` clues, fewer fill-in-blanks);
     `too hard` → lower it; `obscure fill` → shrink the word list (higher frequency cutoff) and add flagged words to the ban list;
     `clever clues` / `boring clues` → increase/decrease the share of wordplay clues (target 25–40% when well received);
     `great theme` / `weak theme` → favor/avoid that themeType, and require a revealer when weak.
   - Solve time vs. difficulty: if median `solveTimeSec` on “hard” is below the “medium” median, recalibrate labels.
   - `usedReveal: true` with low stars usually means a bad crossing: note the puzzle's rare-word crossings and avoid similar ones.
4. Read free-text notes for specific complaints (a named word or clue) and add them to the ban list / clue notes.
5. Record what was changed in the new puzzle's `meta.notes` so the effect can be measured in the next ratings export.

## Generator
The fill engine lives in `/workspace/gen` (box scratch): `fill3.py` (arc-consistent backtracking filler over a
wordfreq∩ENABLE list ranked by frequency) and `hunt.py` (searches symmetric block patterns around fixed theme entries).
Words from minis/themed grids are then hand-reviewed and every clue is written by hand.
