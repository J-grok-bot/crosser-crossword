# Credits and licenses

## Original puzzles (Originals tab)
All puzzles in `puzzles.js` / `tools/puzzles_src.json` are original to Crosser (grids and clues).

## Community puzzles (Community tab)
| Puzzle | Constructor | Source | License | Changes |
|---|---|---|---|---|
| JP Quick #1 | James Penn (JP) | https://github.com/jamesp/crosswords/blob/main/crosswords/jp-puzzle3.json | CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/) | Converted format; added clue enumerations |
| The Mostly-Modular Crossword | xoxomodular | https://github.com/xoxomodular/themostlymodularcrosswordpuzzle | CC0 1.0 (https://creativecommons.org/publicdomain/zero/1.0/) | None (original .puz) |
| Cross Culture: South India | Aakanksha B | https://github.com/aakpaak/crossculturepuzzle | CC0 1.0 (https://creativecommons.org/publicdomain/zero/1.0/) | Converted format |

Original source files are kept in `community/src/`; `community/manifest.json` records credits and licenses and
`node tools/build_community.js` regenerates `community/puzzles.js`. Only add puzzles whose license explicitly permits redistribution.

## Word lists used for construction and validation
- Crossword Nexus Collaborative Word List — https://github.com/Crossword-Nexus/collaborative-word-list — MIT License,
  Copyright (c) 2021 Crossword-Nexus. A filtered subset is in `tools/cwl50.txt`. Used for grid fill and validation.
- ENABLE word list (public domain) — `tools/enable1.txt`, used for validation.
- Spread the Word(list) by Brooke Husic and Enrique Henestroza Anguiano — https://www.spreadthewordlist.com — CC BY-NC-SA 4.0.
  Used as a reference while filling some grids; not redistributed here.

MIT license text for the Collaborative Word List:
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions: The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.
