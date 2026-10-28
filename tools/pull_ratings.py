#!/usr/bin/env python3
"""Pull Crosser ratings snapshots from ntfy and merge them into ratings.json (local only, gitignored).

Usage: python3 tools/pull_ratings.py [--topic crosser-r-...] [--out ratings.json] [--quiet]
Idempotent: union by puzzleId, newest ratedAt wins, old ratings are never dropped.
ntfy only caches ~12h, so run this every few hours (the app also re-sends a snapshot every 6h when opened).
"""
import json, os, sys, urllib.request, argparse, datetime, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_TOPIC = 'crosser-r-486c8a1c2475e45c41e7ff5507636f23'

def fetch(topic):
    url = f'https://ntfy.sh/{topic}/json?poll=1&since=all'
    req = urllib.request.Request(url, headers={'User-Agent': 'crosser-pull/1'})
    with urllib.request.urlopen(req, timeout=30) as r:
        for line in r.read().decode('utf-8', 'replace').splitlines():
            line = line.strip()
            if not line: continue
            try: ev = json.loads(line)
            except ValueError: continue
            if ev.get('event') != 'message': continue
            try: body = json.loads(ev.get('message') or '')
            except ValueError: continue
            if isinstance(body, dict) and body.get('schema') == 'crosser-ratings/1':
                yield ev, body

def valid(r):  # puzzleIds starting with "__test" are connectivity probes and are always ignored
    return isinstance(r, dict) and isinstance(r.get('puzzleId'), str) and not r['puzzleId'].startswith('__test') and isinstance(r.get('stars'), int) \
        and 1 <= r['stars'] <= 5 and isinstance(r.get('ratedAt'), str)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--topic', default=os.environ.get('CROSSER_RATINGS_TOPIC', DEFAULT_TOPIC))
    ap.add_argument('--out', default=os.path.join(ROOT, 'ratings.json'))
    ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args()
    db = {'schema': 'crosser-ratings/1', 'ratings': [], 'seenMessages': []}
    if os.path.exists(a.out):
        with open(a.out) as f: db.update(json.load(f))
    by = {r['puzzleId']: r for r in db['ratings'] if valid(r)}
    seen = set(db.get('seenMessages') or [])
    new_msgs = added = updated = 0
    try:
        msgs = list(fetch(a.topic))
    except Exception as e:
        print(f'pull_ratings: fetch failed ({e}); ratings.json unchanged', file=sys.stderr); return 1
    for ev, body in msgs:
        if ev.get('id') not in seen: new_msgs += 1; seen.add(ev.get('id'))
        for r in body.get('ratings') or []:
            if not valid(r): continue
            r = {k: r.get(k) for k in ('puzzleId','stars','tags','note','ratedAt','solved','solveTimeSec','usedReveal','meta')}
            old = by.get(r['puzzleId'])
            if old is None: by[r['puzzleId']] = r; added += 1
            elif r['ratedAt'] > old['ratedAt']: by[r['puzzleId']] = r; updated += 1
    db['ratings'] = sorted(by.values(), key=lambda r: r['ratedAt'])
    db['seenMessages'] = sorted(seen)[-2000:]
    if added or updated or new_msgs or not os.path.exists(a.out):
        db['updatedAt'] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(a.out), suffix='.tmp')
        with os.fdopen(fd, 'w') as f: json.dump(db, f, indent=1)
        os.replace(tmp, a.out)
    if not a.quiet:
        print(f'pull_ratings: {len(msgs)} snapshot msgs in cache ({new_msgs} new); +{added} new, {updated} updated; {len(by)} ratings total -> {a.out}')
    return 0

if __name__ == '__main__':
    sys.exit(main())
