#!/usr/bin/env python3
"""Fill-quality checks shared by build.py / ingest.py / audit.py.
within(p)  -> (errors, warnings)   (a) duplicate answers, (b) shared roots/stems, (c) clue echoes its own or a crossing answer
reuse(p, backlog) -> (errors, warnings, stats)   (d) cross-puzzle reuse against the live backlog + stoplist
Messages refer to entries by clue number only (e.g. "17-Across"), never by answer text, so reports stay spoiler-free."""
import re,os,itertools,collections
here=os.path.dirname(os.path.abspath(__file__))
_D=None
def dict_words():
    global _D
    if _D is None:
        _D=set()
        for f in ('enable1.txt','cwl50.txt'):
            fp=os.path.join(here,f)
            if os.path.exists(fp):_D|={w.strip().upper() for w in open(fp)}
    return _D
SUF=['INGS','ING','IEST','IER','IES','IED','ERS','EST','ED','ER','ES','EN','LY','S']
def stem(w):
    for s in SUF:
        if w.endswith(s) and len(w)-len(s)>=3:return w[:-len(s)]
    return w
def entries(grid):
    g=[r.upper() for r in grid];n=len(g);w=len(g[0])
    W=lambda r,c:0<=r<n and 0<=c<w and g[r][c] not in '#.'
    out=[];num=0
    for r in range(n):
        for c in range(w):
            if not W(r,c):continue
            a=not W(r,c-1) and W(r,c+1);d=not W(r-1,c) and W(r+1,c)
            if a or d:num+=1
            if a:
                cs=[];k=c
                while W(r,k):cs.append((r,k));k+=1
                out.append(dict(num=num,dir='across',label=f'{num}-Across',cells=cs,word=''.join(g[x][y] for x,y in cs)))
            if d:
                cs=[];k=r
                while W(k,c):cs.append((k,c));k+=1
                out.append(dict(num=num,dir='down',label=f'{num}-Down',cells=cs,word=''.join(g[x][y] for x,y in cs)))
    return out
def _lcs(a,b):
    best=''
    for i in range(len(a)):
        j=i+len(best)+1
        while j<=len(a) and a[i:j] in b:best=a[i:j];j+=1
    return best
def clue_for(p,e):
    cl=p.get('clues',{})
    if isinstance(cl.get('across'),dict):return str(cl[e['dir']].get(str(e['num']),''))
    return str(cl.get(f"{e['word']}/{e['dir'][0]}",cl.get(e['word'],'')))
def tokens(t):
    t=re.sub(r'\{[AD]:[A-Z]+\}',' ',t)          # cross-reference placeholders are not echoes
    t=re.sub(r'\b\d+-(Across|Down)\b',' ',t,flags=re.I)
    return [x for x in re.findall(r"[A-Za-z]+",t.replace("'",'')) ]
PRE=['UNDER','OVER','DIS','MIS','PRE','OUT','UN','RE','IN','IM','EN','A']
def unprefix(w):
    D=dict_words();out={w}
    for x in PRE:
        r=w[len(x):]
        if w.startswith(x) and len(r)>=4 and (r in D or stem(r) in D):out.add(r)
    return out
def same_root(a,b):
    if a==b:return True
    if len(a)>=5 and len(b)>=5:
        for x in unprefix(a):
            for y in unprefix(b):
                if (x,y)!=(a,b) and _core_same(x,y):return True
    return _core_same(a,b)
def _core_same(a,b):
    if a==b:return True
    s,L=(a,b) if len(a)<=len(b) else (b,a)
    if len(s)>=4 and s in L:return True
    sa,sb=stem(a),stem(b)
    if len(sa)>=3 and sa==sb:return True
    if len(s)==3 and (L.startswith(s)) and stem(L)==s:return True
    return False
def within(p):
    E=[];Wn=[];es=entries(p['grid'])
    c=collections.Counter(e['word'] for e in es)
    for w,k in c.items():
        if k>1:E.append('(a) duplicate answer at '+' and '.join(e['label'] for e in es if e['word']==w))
    D=dict_words()
    for x,y in itertools.combinations(es,2):
        if x['word']==y['word']:continue
        if same_root(x['word'],y['word']):E.append(f"(b) {x['label']} and {y['label']} share a root")
        else:
            s=_lcs(x['word'],y['word'])
            if len(s)>=5 or (len(s)==4 and s in D and (x['word'].startswith(s) or x['word'].endswith(s)) and (y['word'].startswith(s) or y['word'].endswith(s))):
                Wn.append(f"(b?) {x['label']} and {y['label']} share a {len(s)}-letter chunk; check by hand")
    cellmap=collections.defaultdict(list)
    for e in es:
        for cc in e['cells']:cellmap[cc].append(e)
    for e in es:
        toks=[t.upper() for t in tokens(clue_for(p,e))]
        cross={id(o):o for cc in e['cells'] for o in cellmap[cc] if o is not e}.values()
        for t in toks:
            if len(t)<3:continue
            if same_root(t,e['word']) and (len(t)>=4 or t==e['word']):E.append(f"(c) clue for {e['label']} contains its own answer");break
        for o in cross:
            if any(len(t)>=3 and (t==o['word'] or (len(stem(t))>=3 and stem(t)==stem(o['word']))) for t in toks):
                E.append(f"(c) clue for {e['label']} contains the crossing answer at {o['label']}")
        for o in es:
            if o is e or o in cross:continue
            if any(len(t)>=4 and t==o['word'] for t in toks):Wn.append(f"(c?) clue for {e['label']} uses the answer at {o['label']}")
    return E,Wn
# ---------- cross-puzzle reuse (d) ----------
# Limits tuned on the Oct 25 2026 backlog (16 live + 2 queued puzzles; see PUZZLE_GUIDE.md).
# minlen/max: answers of at least `minlen` letters that already appear in ANY live puzzle; more than `max` fails.
# any3: cap on repeats of any length (3+). Identical answer+clue pairs already live always fail.
LIMITS={'mini':dict(minlen=4,max=1,any3=2),'midi':dict(minlen=5,max=2,any3=6),'full':dict(minlen=5,max=3,any3=10)}
def kind(p):
    n=len(p['grid']);return 'mini' if n<=7 else 'midi' if n<=12 else 'full'
def load_stoplist():
    f=os.path.join(here,'stoplist.txt')
    if not os.path.exists(f):return set()
    return {l.strip().upper() for l in open(f) if l.strip() and not l.startswith('#')}
def norm(t):return re.sub(r'[^a-z0-9]+',' ',str(t).lower()).strip()
def backlog_index(puzzles,exclude=None):
    idx=collections.defaultdict(set);idx_clues=collections.defaultdict(set)
    for q in puzzles:
        if exclude is not None and q.get('id')==exclude:continue
        for e in entries(q['grid']):
            idx[e['word']].add(q.get('id'));idx_clues[e['word']].add(norm(clue_for(q,e)))
    return _Idx(idx,idx_clues)
class _Idx(dict):
    def __init__(s,a,c):super().__init__(a);s.clues=c
def reuse(p,idx,stop=None):
    stop=load_stoplist() if stop is None else stop
    k=kind(p);L=LIMITS[k];E=[];Wn=[]
    es=entries(p['grid'])
    rep=[e for e in es if len(e['word'])>=L['minlen'] and idx.get(e['word'])]
    allrep=[e for e in es if len(e['word'])>=3 and idx.get(e['word'])]
    same=[e['label'] for e in es if norm(clue_for(p,e)) in idx.clues.get(e['word'],())] if hasattr(idx,'clues') else []
    if same:E.append('(d) answer AND clue identical to a live puzzle at '+', '.join(same))
    if len(allrep)>L['any3']:E.append(f"(d) reuse: {len(allrep)} answers (any length) already used in live puzzles (limit {L['any3']} for a {k})")
    if len(rep)>L['max']:
        E.append(f"(d) reuse: {len(rep)} answers of {L['minlen']}+ letters already used in live puzzles (limit {L['max']} for a {k}): "+', '.join(e['label'] for e in rep))
    elif rep:Wn.append(f"(d) reuse: {len(rep)} answer(s) of {L['minlen']}+ letters already live (limit {L['max']}): "+', '.join(e['label'] for e in rep))
    st=[e['label'] for e in es if e['word'] in stop]
    if st:Wn.append('(d) stoplist answers at '+', '.join(st))
    return E,Wn,dict(kind=k,repeats=len(rep),limit=L['max'],minlen=L['minlen'],anyRepeats=len(allrep),any3=L['any3'],sameClue=len(same),entries=len(es),stoplist=len(st))
