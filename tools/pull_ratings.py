#!/usr/bin/env python3
"""Pull Crosser ratings snapshots from ntfy and merge them into ratings.json (local only, gitignored).

Usage: python3 tools/pull_ratings.py [--topic crosser-r-...] [--out ratings.json] [--quiet]
Idempotent: ratings are keyed by (deviceId, puzzleId). Within one device the newest ratedAt wins (a re-rate edits
that device's rating); across devices every rating is kept. Ratings without a deviceId (older app versions / older
ratings.json files) get LEGACY_DEVICE. Ratings are never dropped.
ntfy only caches ~12h, so run this every few hours (the app also re-sends a snapshot every 6h when opened).
"""
import json, os, sys, urllib.request, argparse, datetime, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_TOPIC = 'crosser-r-486c8a1c2475e45c41e7ff5507636f23'
LEGACY_DEVICE = 'legacy'
FIELDS = ('deviceId','puzzleId','stars','tags','note','ratedAt','solved','solveTimeSec','usedReveal','meta')

def dev_of(r, fallback=None):
    d = r.get('deviceId') or fallback
    return d if isinstance(d, str) and d.strip() else LEGACY_DEVICE

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
    db_in_keyed = db.get('keyedBy')  # None for pre-device files (and new files)
    by = {}
    for r in db.get('ratings') or []:  # migrate: entries without deviceId -> legacy device; keep everything valid
        if not valid(r): continue
        r = dict(r); r['deviceId'] = dev_of(r)
        k = (r['deviceId'], r['puzzleId'])
        if k not in by or r['ratedAt'] > by[k]['ratedAt']: by[k] = r
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
            r = {k: r.get(k) for k in FIELDS}
            r['deviceId'] = dev_of(r, body.get('deviceId'))
            k = (r['deviceId'], r['puzzleId'])
            old = by.get(k)
            if old is None: by[k] = r; added += 1
            elif r['ratedAt'] > old['ratedAt']: by[k] = r; updated += 1
    # A legacy (no-deviceId) copy of a rating that later arrived with its device id is the same rating, not a second one:
    # same puzzleId + identical millisecond ratedAt. Fold it into the device entry instead of double-counting.
    dev_keys = {(r['puzzleId'], r['ratedAt']) for k, r in by.items() if k[0] != LEGACY_DEVICE}
    for k in [k for k, r in by.items() if k[0] == LEGACY_DEVICE and (r['puzzleId'], r['ratedAt']) in dev_keys]:
        del by[k]
        if added: added -= 1
    db['ratings'] = sorted(by.values(), key=lambda r: (r['ratedAt'], r['deviceId'], r['puzzleId']))
    db['keyedBy'] = 'deviceId+puzzleId'
    db['seenMessages'] = sorted(seen)[-2000:]
    migrated = db_in_keyed != 'deviceId+puzzleId'
    if added or updated or new_msgs or migrated or not os.path.exists(a.out):
        db['updatedAt'] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(a.out), suffix='.tmp')
        with os.fdopen(fd, 'w') as f: json.dump(db, f, indent=1)
        os.replace(tmp, a.out)
    if not a.quiet:
        print(f'pull_ratings: {len(msgs)} snapshot msgs in cache ({new_msgs} new); +{added} new, {updated} updated; {len(by)} ratings total from {len({k[0] for k in by})} device(s) -> {a.out}')
    return 0

if __name__ == '__main__':
    sys.exit(main())
