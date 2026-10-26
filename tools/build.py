#!/usr/bin/env python3
"""Validate puzzle sources (puzzles_src.json) and emit ../puzzles.js.
Checks: square grid, 180° rotational symmetry, no entries < 3 letters, every white cell checked
(in both an across and a down entry), connectivity, unique entries, every entry has a clue,
no unused clues, and every answer appears in a word list (ENABLE or Crossword Nexus Collaborative Word List score>=50) unless listed in 'phrases'.
Also runs tools/quality.py: (a) duplicate answers, (b) shared roots, (c) clue echoing its own/crossing answer,
(d) reuse vs. earlier live puzzles. For already-live puzzles these print as grandfathered notes (use --strict to fail);
ingest.py enforces them as hard failures on new puzzles via full_check()."""
import json,sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import quality
here=os.path.dirname(os.path.abspath(__file__))
src=json.load(open(os.path.join(here,'puzzles_src.json')))
words=set()
wl=os.path.join(here,'enable1.txt')
if os.path.exists(wl): words={w.strip().upper() for w in open(wl)}
sw=os.path.join(here,'cwl50.txt')
if os.path.exists(sw): words|={w.strip().upper() for w in open(sw)}
def entries(g):
    n=len(g);W=lambda r,c:0<=r<n and 0<=c<n and g[r][c]!='#'
    num=0;out={'across':{},'down':{}};chk={}
    for r in range(n):
        for c in range(n):
            if not W(r,c):continue
            a=not W(r,c-1) and W(r,c+1);d=not W(r-1,c) and W(r+1,c)
            if a or d:num+=1
            if a:
                k=c;s=''
                while W(r,k):s+=g[r][k];chk.setdefault((r,k),set()).add('a');k+=1
                out['across'][num]=s
            if d:
                k=r;s=''
                while W(k,c):s+=g[k][c];chk.setdefault((k,c),set()).add('d');k+=1
                out['down'][num]=s
    return out,chk
def check(p):
    E=[]
    for k in ('id','title','grid','clues'):
        if k not in p: return [f'missing field {k}'],p,0,0
    g=[r.upper() for r in p['grid']];p['grid']=g;n=len(g)
    if not all(ch=='#' or 'A'<=ch<='Z' for r in g for ch in r):E.append('grid has characters other than A-Z and #')
    if any(len(r)!=n for r in g):E.append('not square')
    for r in range(n):
        for c in range(n):
            if (g[r][c]=='#')!=(g[n-1-r][n-1-c]=='#'):E.append(f'asymmetric at {r},{c}')
    ent,chk=entries(g)
    for r in range(n):
        for c in range(n):
            if g[r][c]!='#' and chk.get((r,c))!={'a','d'}:E.append(f'unchecked cell {r},{c}')
    allw=[w for d in ent for w in ent[d].values()]
    for w in allw:
        if len(w)<3:E.append('short entry '+w)
        if words and w not in words and w not in set(p.get('phrases',[])):E.append('not in word list: '+w)
    if len(set(allw))!=len(allw):E.append('duplicate entries')
    lim={15:78,13:66,11:44}.get(n)
    if lim and len(allw)>lim:E.append(f'too many words {len(allw)}>{lim}')
    cells={(r,c) for r in range(n) for c in range(n) if g[r][c]!='#'}
    if cells:
        st=[next(iter(cells))];seen=set(st)
        while st:
            r,c=st.pop()
            for x in ((r+1,c),(r-1,c),(r,c+1),(r,c-1)):
                if x in cells and x not in seen:seen.add(x);st.append(x)
        if seen!=cells:E.append('grid not connected')
    for k,v in p['clues'].items():
        if not str(v).strip():E.append('empty clue '+k)
    clues={'across':{},'down':{}}
    byans=p['clues']
    for d in ent:
        for k,w in ent[d].items():
            key=w if w in byans else f'{w}/{d[0]}'
            if key not in byans and f'{w}/{d[0]}' in byans:key=f'{w}/{d[0]}'
            if key not in byans:E.append(f'missing clue {k}{d[0].upper()} {w}');continue
            clues[d][str(k)]=byans[key]
    used={w for w in allw}|{f'{w}/{d[0]}' for d in ent for w in ent[d].values()}
    for k in byans:
        if k not in used:E.append('unused clue '+k)
    # resolve "N-Across" style references: {A:WORD} -> number
    def ref(t):
        import re
        def f(m):
            d,w=m.group(1),m.group(2);dd='across' if d=='A' else 'down'
            for k,v in ent[dd].items():
                if v==w:return f"{k}-{'Across' if d=='A' else 'Down'}"
            E.append('bad ref '+w);return w
        return re.sub(r'\{([AD]):([A-Z]+)\}',f,t)
    for d in clues:
        for k in clues[d]:clues[d][k]=ref(clues[d][k])
    q={k:v for k,v in p.items() if k not in('clues','phrases')};q['clues']=clues
    q.setdefault('meta',{})['wordCount']=len(allw)
    return E,q,len(allw),sum(r.count('#') for r in g)
def full_check(p,backlog):
    """Structural check + quality (a)(b)(c) + cross-puzzle reuse (d) against `backlog` (list of live puzzles).
    Returns (errors, warnings, built, words, blocks, reuse_stats). Used by ingest.py for NEW puzzles (hard fail)."""
    raw=json.loads(json.dumps(p))
    E,q,nw,nb=check(raw)
    QE,QW=quality.within(p)
    RE,RW,st=quality.reuse(p,quality.backlog_index(backlog,exclude=p.get('id')))
    return E+QE+RE,QW+RW,q,nw,nb,st
def main():
    errs=0;outp=[];strict='--strict' in sys.argv
    for i,p in enumerate(src):
        QE,QW=quality.within(p)
        RE,RW,st=quality.reuse(p,quality.backlog_index(src[:i]))
        if QE or RE:print(p['id'],'quality (grandfathered; live backlog is append-only):',*QE,*RE,sep='\n   ')
        E,q,nw,nb=check(p)
        if strict:E=E+QE+RE
        if E:
            errs+=1;print(p['id'],'FAIL');[print('  ',e) for e in E]
        else: print(p['id'],'ok',nw,'words',nb,'blocks')
        outp.append(q)
    open(os.path.join(here,'..','puzzles.js'),'w').write('// Generated by tools/build.py from tools/puzzles_src.json. All puzzles original.\nconst PUZZLES='+json.dumps(outp,indent=1)+';\n')
    sys.exit(1 if errs else 0)
if __name__=='__main__': main()
