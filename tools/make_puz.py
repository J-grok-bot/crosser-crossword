"""Write an Across Lite .puz for a puzzle in puzzles_src (used to test the importer)."""
import json,struct,sys,os
def cksum(data,c=0):
    for b in data:
        c = (c>>1) | ((c&1)<<15); c=(c+b)&0xffff
    return c
def write(p,clues,path):
    g=p['grid'];h=len(g);w=len(g[0])
    sol=''.join(g).replace('#','.').encode('latin1');fill=''.join('.' if ch=='#' else '-' for ch in ''.join(g)).encode()
    order=[]
    for k in sorted(set(int(x) for x in list(clues['across'])+list(clues['down']))):
        if str(k) in clues['across']:order.append(clues['across'][str(k)])
        if str(k) in clues['down']:order.append(clues['down'][str(k)])
    strs=[p['title'],p.get('author',''),'Original'] 
    body=sol+fill+b''.join(s.encode('latin1','replace')+b'\0' for s in strs+order)+b'\0'
    hdr=bytearray(0x34);hdr[2:14]=b'ACROSS&DOWN\0';hdr[0x18:0x1C]=b'1.3\0'
    hdr[0x2C]=w;hdr[0x2D]=h;struct.pack_into('<HHH',hdr,0x2E,len(order),1,0)
    open(path,'wb').write(bytes(hdr)+body)
src=open(os.path.join(os.path.dirname(__file__),'..','puzzles.js')).read()
P=json.loads(src[src.index('['):src.rindex(']')+1])
p=[x for x in P if x['id']==sys.argv[1]][0]
write(p,p['clues'],sys.argv[2])
