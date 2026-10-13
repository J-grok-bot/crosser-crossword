'use strict';
// Across Lite .puz and .ipuz importer -> internal {id,title,author,grid,clues}
async function importFile(f){
  const name=f.name.toLowerCase();
  if(name.endsWith('.puz')) return parsePuz(new Uint8Array(await f.arrayBuffer()),f.name);
  return parseIpuz(JSON.parse(await f.text()),f.name);
}
function parsePuz(b,fname){
  const dv=new DataView(b.buffer,b.byteOffset,b.byteLength);
  const magic=String.fromCharCode(...b.slice(2,14));if(magic!=='ACROSS&DOWN\0')throw new Error('not a .puz file');
  const w=b[0x2C],h=b[0x2D],nclues=dv.getUint16(0x2E,true),scr=dv.getUint16(0x32,true);
  if(scr&0x0004)throw new Error('scrambled puzzles are not supported');
  let o=0x34;const sol=String.fromCharCode(...b.slice(o,o+w*h));o+=2*w*h;
  const dec=new TextDecoder('iso-8859-1');
  const str=()=>{let e=o;while(b[e]!==0)e++;const s=dec.decode(b.slice(o,e));o=e+1;return s;};
  const title=str(),author=str(),copy=str();const clueList=[];for(let i=0;i<nclues;i++)clueList.push(str());
  const grid=[];for(let r=0;r<h;r++)grid.push(sol.slice(r*w,r*w+w).replace(/\./g,'#'));
  // rebar: numbering order — across before down at each numbered cell
  const isW=(r,c)=>r>=0&&c>=0&&r<h&&c<w&&grid[r][c]!=='#';
  const clues={across:{},down:{}};let k=0,num=0;
  for(let r=0;r<h;r++)for(let c=0;c<w;c++){if(!isW(r,c))continue;const a=!isW(r,c-1)&&isW(r,c+1),d=!isW(r-1,c)&&isW(r+1,c);
    if(a||d)num++;if(a)clues.across[num]=clueList[k++];if(d)clues.down[num]=clueList[k++];}
  return {id:'import-'+hash(sol+title),title:title||fname,author,source:copy||'Imported',grid,clues};
}
function parseIpuz(j,fname){
  const sol=j.solution,h=sol.length,w=sol[0].length;
  const val=x=>x===null||x==='#'||(x&&x.cell==='#')?'#':(typeof x==='object'?(x.value||x.cell||'?'):String(x));
  const grid=sol.map(r=>r.map(x=>{const v=val(x);return v==='#'?'#':v[0].toUpperCase();}).join(''));
  const clues={across:{},down:{}};
  for(const [k,arr] of Object.entries(j.clues||{})){const d=k.toLowerCase().startsWith('across')?'across':'down';
    for(const c of arr){if(Array.isArray(c))clues[d][c[0]]=c[1];else clues[d][c.number]=c.clue;}}
  return {id:'import-'+hash(grid.join('')),title:j.title||fname,author:j.author||'',source:j.copyright||'Imported',grid,clues};
}
function hash(s){let x=5381;for(let i=0;i<s.length;i++)x=(x*33^s.charCodeAt(i))>>>0;return x.toString(36);}
if(typeof module!=='undefined')module.exports={parsePuz,parseIpuz};
