#!/usr/bin/env python3
"""Ingest puzzles from /workspace/puzzler-out/*.json (one puzzle object or a list, in puzzles_src format).
Each puzzle is validated with build.check(); passing ones are added/updated in puzzles_src.json,
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
        E,q,nw,nb=build.check(json.loads(json.dumps(p)))
        if E:report['rejected'].append({'file':f,'id':p.get('id'),'errors':E});continue
        if p['id'] in ids:
            if src[ids[p['id']]]==p:continue
            src[ids[p['id']]]=p
        else:ids[p['id']]=len(src);src.append(p)
        changed=True;report['accepted'].append({'file':f,'id':p['id'],'words':nw,'blocks':nb})
json.dump(report,open(os.path.join(d,'_ingest_report.json'),'w'),indent=1)
print(json.dumps(report,indent=1))
if changed and '--dry-run' not in args:
    json.dump(src,open(srcp,'w'),indent=1)
    r=subprocess.run([sys.executable,os.path.join(here,'build.py')])
    if r.returncode:print('build failed; not pushing');sys.exit(1)
    if '--push' in args:
        root=os.path.dirname(here)
        subprocess.run(['git','-C',root,'add','tools/puzzles_src.json','puzzles.js'],check=True)
        ids_=', '.join(a['id'] for a in report['accepted'])
        subprocess.run(['git','-C',root,'commit','-qm','Add puzzles: '+ids_],check=True)
        subprocess.run(['git','-C',root,'push','-q'],check=True)
        print('pushed')
