#!/usr/bin/env python3
"""Ingest puzzles from /workspace/puzzler-out/*.json (one puzzle object or a list, in puzzles_src format).
APPEND-ONLY: existing puzzles are never modified or removed; id collisions get a new unique id.
Each puzzle is validated with build.full_check() (structure + within-puzzle quality + cross-puzzle reuse vs. the live backlog); passing ones are appended in puzzles_src.json,
puzzles.js is rebuilt, and (with --push) the change is committed and pushed.
Results are written to /workspace/puzzler-out/_ingest_report.json.
Usage: python3 tools/ingest.py [--dir DIR] [--push] [--dry-run]"""
import json,os,sys,glob,subprocess,datetime
here=os.path.dirname(os.path.abspath(__file__));sys.path.insert(0,here)
import build
args=sys.argv[1:];d=args[args.index('--dir')+1] if '--dir' in args else '/workspace/puzzler-out'
srcp=os.path.join(here,'puzzles_src.json');src=json.load(open(srcp));ids={p['id']:i for i,p in enumerate(src)}
report={'ranAt':datetime.datetime.now().isoformat(),'accepted':[],'rejected':[]};changed=False
for f in sorted(glob.glob(os.path.join(d,'*.json'))):
    if os.path.basename(f).startswith('_'):continue
    try:data=json.load(open(f))
    except Exception as e:report['rejected'].append({'file':f,'errors':['bad JSON: '+str(e)]});continue
    for p in (data if isinstance(data,list) else [data]):
        p.setdefault('author','Crosser');p.setdefault('meta',{})
        body=lambda x:json.dumps({k:x.get(k) for k in ('grid','clues')},sort_keys=True)
        if any(body(e)==body(p) for e in src):continue  # already shipped (append-only, no duplicates)
        E,Wn,q,nw,nb,st=build.full_check(p,src)
        if E:report['rejected'].append({'file':f,'id':p.get('id'),'errors':E,'warnings':Wn,'reuse':st});continue
        base=p['id'];k=2
        while p['id'] in ids:p['id']=f"{base}-{k}";k+=1  # never overwrite: give a fresh unique id
        p.pop('addedDate',None);p['addedDate']=datetime.datetime.now(__import__('zoneinfo').ZoneInfo('America/New_York')).date().isoformat()
        ids[p['id']]=len(src);src.append(p)
        changed=True;report['accepted'].append({'file':f,'id':p['id'],'words':nw,'blocks':nb,'warnings':Wn,'reuse':st})
json.dump(report,open(os.path.join(d,'_ingest_report.json'),'w'),indent=1)
print(json.dumps(report,indent=1))
if changed and '--dry-run' not in args:
    json.dump(src,open(srcp,'w'),indent=1)
    subprocess.run([sys.executable,os.path.join(here,'make_stoplist.py')])
    r=subprocess.run([sys.executable,os.path.join(here,'build.py')])
    if r.returncode:print('build failed; not pushing');sys.exit(1)
    if '--push' in args:
        root=os.path.dirname(here)
        subprocess.run(['git','-C',root,'add','tools/puzzles_src.json','puzzles.js','tools/stoplist.txt'],check=True)
        ids_=', '.join(a['id'] for a in report['accepted'])
        subprocess.run(['git','-C',root,'commit','-qm','Add puzzles: '+ids_],check=True)
        subprocess.run(['git','-C',root,'push','-q'],check=True)
        print('pushed')
