#!/usr/bin/env python3
"""Turn ratings.json into ratings_brief.md for puzzle constructors (local only, gitignored).

Usage: python3 tools/ratings_brief.py [--ratings ratings.json] [--out ratings_brief.md]

Principles (see PUZZLE_GUIDE.md "How future generation should use ratings"):
  * Asymmetric: negative signals weigh ~2x positive ones; avoiding what made bad puzzles bad beats copying good ones.
  * AVOID targets specific flaws / execution problems, never whole categories. A category (theme type, difficulty,
    clue style, size) is only down-weighted when it is consistently low across 3+ ratings, and is never excluded.
  * Diversity: positive ratings must not narrow the mix; the brief reports the recent mix and asks for variety.
  * Multi-device: ratings.json holds one rating per (deviceId, puzzleId). Every device's rating counts as its own
    rating everywhere (weights, tag totals, category means, per-puzzle averages, n). Nothing is de-duplicated by puzzle.
The brief describes traits only (no answers or grid contents are printed).
"""
import json, os, re, sys, argparse, datetime, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEG_W, POS_W, NEUTRAL_W = 2.0, 1.0, 0.5
NEG_TAGS = {
    'too easy': 'Difficulty undershot: add misdirection and more `?`/wordplay clues, fewer fill-in-the-blanks and dictionary-definition clues; keep fair crossings.',
    'too hard': 'Difficulty overshot: avoid stacked obscure crossings, give every proper noun or rare word fair, inferable crosses, ease the clues on long entries.',
    'obscure fill': 'Fill quality: no crosswordese, obscure proper nouns, partials, roll-your-own words or obscure abbreviations; raise the word-list frequency cutoff and rework those corners.',
    'boring clues': 'Clue quality: fewer flat definitions; more lively misdirection, fresh angles, and 25-40% wordplay/`?` clues done well.',
    'weak theme': 'Theme execution: tighten the theme so every themer follows the rule exactly and consistently, the payoff is clear, and add a revealer if it helps. This is about execution, not a ban on that theme type.',
}
POS_TAGS = {
    'fun': 'overall enjoyment', 'great theme': 'a tight, satisfying theme payoff',
    'clever clues': 'clever, fair misdirection in clues', 'smooth fill': 'clean, familiar fill with few compromises',
}
THEME_MECHANISMS = ['starts-with', 'ends-with', 'hidden-word', 'added-letter', 'removed-letter', 'letter-swap',
    'anagram', 'homophone/pun', 'reversal', 'spoonerism', 'compound-split', 'phrase-pattern', 'category/list',
    'wacky phrases', 'themeless (full-size, low word count)']

def load_js_array(path, var):
    s = open(path).read()
    i = s.index('[', s.index(var)); j = s.rindex(']')
    return json.loads(s[i:j+1])

def load_puzzles():
    ps = json.load(open(os.path.join(ROOT, 'tools', 'puzzles_src.json')))
    try: ps += load_js_array(os.path.join(ROOT, 'community', 'puzzles.js'), 'COMMUNITY_PUZZLES')
    except Exception: pass
    return {p['id']: p for p in ps}

def family(theme):
    t = (theme or 'unknown').lower().strip()
    return re.split(r'[\s(]', t, maxsplit=1)[0] or 'unknown'

def traits(p):
    g = p['grid']; h, w = len(g), len(g[0])
    blocks = sum(r.count('#') for r in g)
    cl = p.get('clues') or {}
    if 'across' in cl or 'down' in cl: clues = [c for d in ('across', 'down') for c in (cl.get(d) or {}).values()]
    else: clues = list(cl.values())  # puzzles_src.json keys clues by entry; only clue text is used, never printed
    clues = [c if isinstance(c, str) else str(c) for c in clues]
    n = max(1, len(clues))
    m = p.get('meta') or {}
    def share(f): return round(100 * sum(1 for c in clues if f(c)) / n)
    lens = []
    for rows in (g, [''.join(r[i] for r in g) for i in range(w)]):
        for r in rows: lens += [len(x) for x in r.split('#') if len(x) >= 2]
    return {
        'size': f'{w}x{h}', 'difficulty': m.get('difficulty', 'unknown'), 'themeType': m.get('themeType', 'unknown'),
        'themeFamily': family(m.get('themeType')), 'clueStyle': m.get('clueStyle', 'unknown'),
        'wordCount': m.get('wordCount') or len(lens), 'blocks': blocks,
        'qClues%': share(lambda c: c.rstrip().endswith('?')),
        'blankClues%': share(lambda c: '___' in c or '__' in c),
        'abbrClues%': share(lambda c: re.search(r'\babbr\b|\bfor short\b|\binits?\.|\binitials\b', c, re.I) is not None),
        'longEntries(8+)': sum(1 for L in lens if L >= 8), 'threeLetter%': round(100 * sum(1 for L in lens if L == 3) / max(1, len(lens))),
        'source': 'community' if p.get('community') else 'original', 'addedDate': p.get('addedDate') or p.get('date') or '',
    }

def fmt_traits(t):
    return (f"{t['size']}, {t['difficulty']}, theme: {t['themeType']}, clues: {t['clueStyle']}, {t['wordCount']} words, "
            f"{t['blocks']} blocks, `?` clues {t['qClues%']}%, fill-in-blank {t['blankClues%']}%, abbr-type clues {t['abbrClues%']}%, "
            f"3-letter entries {t['threeLetter%']}%, {t['longEntries(8+)']} entries of 8+")

def weight(r, now):
    s = r['stars']
    w = NEG_W if s <= 2 else POS_W if s >= 4 else NEUTRAL_W
    try:
        age = (now - datetime.datetime.fromisoformat(r['ratedAt'].replace('Z', '+00:00'))).days
        if age <= 14: w *= 1.5
    except Exception: pass
    return w

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ratings', default=os.path.join(ROOT, 'ratings.json'))
    ap.add_argument('--out', default=os.path.join(ROOT, 'ratings_brief.md'))
    a = ap.parse_args()
    now = datetime.datetime.now(datetime.timezone.utc)
    puzzles = load_puzzles()
    ratings = []
    if os.path.exists(a.ratings):
        ratings = [r for r in json.load(open(a.ratings)).get('ratings', []) if isinstance(r.get('stars'), int)]
    T = {pid: traits(p) for pid, p in puzzles.items()}
    def tr(r):
        if r['puzzleId'] in T: return T[r['puzzleId']]
        m = r.get('meta') or {}
        return {'size': m.get('size', '?'), 'difficulty': m.get('difficulty', 'unknown'), 'themeType': m.get('themeType', 'unknown'),
                'themeFamily': family(m.get('themeType')), 'clueStyle': m.get('clueStyle', 'unknown'), 'wordCount': m.get('wordCount'),
                'blocks': '?', 'qClues%': '?', 'blankClues%': '?', 'abbrClues%': '?', 'threeLetter%': '?', 'longEntries(8+)': '?'}
    dev = lambda r: 'device ' + (r.get('deviceId') or 'legacy')[-4:] if (r.get('deviceId') or 'legacy') != 'legacy' else 'legacy device'
    ndev = len({r.get('deviceId') or 'legacy' for r in ratings})
    title = lambda r: (puzzles.get(r['puzzleId'], {}).get('title') or (r.get('meta') or {}).get('title') or r['puzzleId'])
    neg = [r for r in ratings if r['stars'] <= 2]
    mid = [r for r in ratings if r['stars'] == 3]
    pos = [r for r in ratings if r['stars'] >= 4]
    L = [f"# Crosser ratings brief (for constructors only)",
         f"Generated {now.astimezone().strftime('%Y-%m-%d %H:%M %Z')} from {len(ratings)} rating(s) across {ndev} device(s): {len(neg)} low (1-2★), {len(mid)} neutral (3★), {len(pos)} high (4-5★).",
         f"Weighting: low ratings and negative tags count {NEG_W:g}x, positive {POS_W:g}x, 3★ {NEUTRAL_W:g}x; ratings from the last 14 days x1.5.",
         "Every device's rating counts separately (two devices rating one puzzle = two ratings).",
         "Priority: fix what made low-rated puzzles bad. Do not clone well-rated ones. Keep the mix varied (see Diversity).", ""]

    # ---------------- AVOID ----------------
    L += ["## 1. AVOID (highest priority: specific flaws, not categories)", ""]
    if not ratings:
        L += ["_No ratings received yet. Follow PUZZLE_GUIDE.md quality rules and the Diversity section below._", ""]
    else:
        tagw = collections.Counter(); tagp = collections.defaultdict(list)
        for r in ratings:
            w = weight(r, now) * (1 if r['stars'] <= 2 else 0.75)  # a negative tag on a 3-5★ puzzle still counts
            for t in r.get('tags') or []:
                if t in NEG_TAGS: tagw[t] += NEG_W * w / (NEG_W if r['stars'] <= 2 else 1); tagp[t].append(r)
        if tagw:
            L += ["### Flagged flaws (weighted)", ""]
            for t, w in tagw.most_common():
                where = '; '.join(f"“{title(r)}” ({r['stars']}★ {dev(r)}, {tr(r)['size']}, {tr(r)['difficulty']}, {tr(r)['themeFamily']})" for r in tagp[t])
                L += [f"- **{t}** (weight {w:.1f}, {len(tagp[t])}×): {NEG_TAGS[t]}", f"  - Seen on: {where}"]
            L.append("")
        if neg:
            L += ["### Low-rated puzzles: what to learn (execution, not category)", ""]
            for r in sorted(neg, key=lambda r: (r['stars'], r['ratedAt'])):
                t = tr(r)
                L.append(f"- **“{title(r)}”** `{r['puzzleId']}`: {r['stars']}★ ({dev(r)})" + (f", tags: {', '.join(r.get('tags') or [])}" if r.get('tags') else ", no tags"))
                if r.get('note'): L.append(f"  - Solver note: “{r['note']}”")
                L.append(f"  - Traits: {fmt_traits(t)}")
                hints = []
                if r.get('usedReveal'): hints.append('solver needed Reveal: check for unfair or obscure crossings in that style of grid')
                if r.get('solved') is False: hints.append('not finished: likely a stuck corner or unfair crossing')
                if isinstance(t.get('blankClues%'), int) and t['blankClues%'] >= 20: hints.append('many fill-in-the-blank clues')
                if isinstance(t.get('abbrClues%'), int) and t['abbrClues%'] >= 10: hints.append('high abbreviation density')
                if isinstance(t.get('threeLetter%'), int) and t['threeLetter%'] >= 35 and t['size'] != '5x5': hints.append('lots of short glue fill')
                if isinstance(t.get('qClues%'), int) and t['qClues%'] <= 5 and 'boring clues' in (r.get('tags') or []): hints.append('almost no wordplay clues')
                if not r.get('tags') and not r.get('note'): hints.append('no reason given: compare its measured traits with well-rated puzzles of the same size and fix the outliers; do NOT ban its theme type or size')
                if hints: L.append("  - Likely causes: " + '; '.join(hints))
            L.append("")
        # per-puzzle aggregate over ALL ratings from all devices
        byp = collections.defaultdict(list)
        for r in ratings: byp[r['puzzleId']].append(r)
        L += ["### Per-puzzle averages (all ratings from all devices)", ""]
        for pid, rs in sorted(byp.items(), key=lambda kv: (sum(r['stars'] for r in kv[1]) / len(kv[1]), kv[0])):
            mean = sum(r['stars'] for r in rs) / len(rs)
            wsum = sum(weight(r, now) for r in rs); wmean = sum(weight(r, now) * r['stars'] for r in rs) / wsum
            lows = sum(1 for r in rs if r['stars'] <= 2)
            L.append(f"- “{title(rs[0])}” `{pid}`: n={len(rs)} from {len({r.get('deviceId') or 'legacy' for r in rs})} device(s), "
                     f"mean {mean:.1f}★ (weighted {wmean:.1f}★, lows count {NEG_W:g}x), stars {sorted(r['stars'] for r in rs)}, {lows} low"
                     + (" (devices disagree: treat the low rating's flaws as real)" if lows and lows < len(rs) else ""))
        L.append("")
        # category down-weighting: only consistent lows across 3+ ratings
        L += ["### Category down-weighting (only consistent lows across 3+ ratings; never exclude)", ""]
        flagged = False
        for dim, key in (('theme type', 'themeFamily'), ('difficulty', 'difficulty'), ('clue style', 'clueStyle'), ('size', 'size')):
            groups = collections.defaultdict(list)
            for r in ratings: groups[tr(r)[key]].append(r)
            for val, rs in groups.items():
                if len(rs) < 3: continue
                mean = sum(r['stars'] for r in rs) / len(rs); lows = sum(1 for r in rs if r['stars'] <= 2)
                if mean <= 2.5 and lows / len(rs) >= 2 / 3:
                    flagged = True
                    L.append(f"- {dim} **{val}**: {len(rs)} ratings, mean {mean:.1f}★, {lows} low. Use it about half as often, still allowed, and fix the flaws above when you do.")
        if not flagged: L.append("- None. No theme type, difficulty, clue style or size is consistently low across 3+ ratings, so nothing is down-weighted. One bad rating is a flaw to fix, not a category to drop.")
        L.append("")

    # ---------------- LEAN TOWARD ----------------
    L += ["## 2. Lean toward (lower priority: qualities, not copies)", ""]
    if not pos:
        L += ["_No 4-5★ ratings yet._", ""]
    else:
        pt = collections.Counter(t for r in pos for t in (r.get('tags') or []) if t in POS_TAGS)
        if pt: L += [f"- Valued qualities: " + '; '.join(f"{POS_TAGS[t]} ({n}×)" for t, n in pt.most_common())]
        for r in sorted(pos, key=lambda r: -r['stars']):
            L.append(f"- “{title(r)}” {r['stars']}★ ({dev(r)})" + (f" ({', '.join(r.get('tags') or [])})" if r.get('tags') else '') + (f": “{r['note']}”" if r.get('note') else ''))
        L += ["- Carry over the *quality* (tight themes, fair misdirection, clean fill). Do NOT reuse the same theme mechanism, clue gimmick or grid pattern just because it rated well.", ""]

    # ---------------- DIVERSITY ----------------
    recent = sorted((p for p in puzzles.values() if not p.get('community')), key=lambda p: (T[p['id']]['addedDate'], p['id']))[-10:]
    L += ["## 3. Diversity (required)", "", f"Recent mix, last {len(recent)} original puzzles (oldest to newest):", ""]
    for p in recent:
        t = T[p['id']]; L.append(f"- {t['addedDate']} `{p['id']}`: {t['size']}, {t['difficulty']}, {t['themeFamily']}, clues {t['clueStyle']}, {t['wordCount']} words / {t['blocks']} blocks, `?` {t['qClues%']}%")
    L.append("")
    for dim, key in (('Sizes', 'size'), ('Difficulty', 'difficulty'), ('Theme mechanisms', 'themeFamily'), ('Clue styles', 'clueStyle')):
        c = collections.Counter(T[p['id']][key] for p in recent)
        L.append(f"- {dim}: " + ', '.join(f"{k} {v}" for k, v in c.most_common()))
    L.append("")
    full = [p for p in recent if T[p['id']]['size'] != '5x5']
    rules = []
    if full:
        last = [T[p['id']]['themeFamily'] for p in full[-2:]]
        rules.append(f"Next full-size puzzle: use a different theme mechanism than the last two full-size ones ({', '.join(last)}).")
    for dim, key in (('difficulty', 'difficulty'), ('clue style', 'clueStyle')):
        for grp, nm in ((full, 'full-size'), ([p for p in recent if T[p['id']]['size'] == '5x5'], 'mini')):
            c = collections.Counter(T[p['id']][key] for p in grp)
            if len(grp) >= 3 and c and c.most_common(1)[0][1] / len(grp) >= 0.7:
                v = c.most_common(1)[0][0]
                rules.append(f"Recent {nm} puzzles are mostly {dim} “{v}”: vary it soon (e.g. a different {dim}), unless ratings above say otherwise.")
    tried = {T[p['id']]['themeFamily'] for p in puzzles.values()}
    untried = [m for m in THEME_MECHANISMS if m.split('/')[0].split(' ')[0] not in tried]
    rules += ["Don't repeat the same theme mechanism, clue style or grid shape back-to-back.",
              "About 1 puzzle in 5 may be exploratory: an untried theme mechanism, clue style or shape, held to the same quality bar. Untried mechanisms: " + ', '.join(untried) + ".",
              "Positive ratings must not narrow the mix; negative ratings fix flaws, they don't remove categories."]
    L += ["Rules for the next build:", ""] + [f"- {x}" for x in rules] + [""]
    open(a.out, 'w').write('\n'.join(L))
    print(f'ratings_brief: {len(ratings)} ratings -> {a.out}')

if __name__ == '__main__':
    main()
