'use strict';
// ---------- puzzle model ----------
function buildModel(p){
  const n=p.grid.length, w=p.grid[0].length, cells=[];
  for(let r=0;r<n;r++)for(let c=0;c<w;c++){const ch=p.grid[r][c];cells.push({r,c,blk:ch==='#'||ch==='.',ans:ch==='#'||ch==='.'?null:ch.toUpperCase(),num:0});}
  const at=(r,c)=>r>=0&&c>=0&&r<n&&c<w?cells[r*w+c]:null;
  const isW=(r,c)=>{const x=at(r,c);return x&&!x.blk};
  const words={across:[],down:[]};let num=0;
  for(let r=0;r<n;r++)for(let c=0;c<w;c++){if(!isW(r,c))continue;
    const sa=!isW(r,c-1)&&isW(r,c+1), sd=!isW(r-1,c)&&isW(r+1,c);
    if(sa||sd){num++;at(r,c).num=num;}
    if(sa){const cs=[];for(let k=c;isW(r,k);k++)cs.push(r*w+k);words.across.push({num,dir:'across',cells:cs});}
    if(sd){const cs=[];for(let k=r;isW(k,c);k++)cs.push(k*w+c);words.down.push({num,dir:'down',cells:cs});}
  }
  for(const d of ['across','down'])for(const wd of words[d]){
    wd.answer=wd.cells.map(i=>cells[i].ans).join('');
    wd.clue=(p.clues[d]||{})[wd.num]||'';
    wd.cells.forEach(i=>cells[i][d]=wd);
  }
  return {p,n,w,cells,words,at};
}
// ---------- state ----------
let M=null,S=null,cur=0,dir='across',pencil=false,timerH=null,paused=false;
const $=id=>document.getElementById(id);
const store={get:k=>{try{return JSON.parse(localStorage.getItem('xw:'+k))}catch(e){return null}},set:(k,v)=>{try{localStorage.setItem('xw:'+k,JSON.stringify(v))}catch(e){}}};
function allPuzzles(){return PUZZLES.concat(store.get('imported')||[]);}
function save(){if(M)store.set('p:'+M.p.id,S);}
function fresh(){return {fill:M.cells.map(()=>''),pen:M.cells.map(()=>false),rev:M.cells.map(()=>false),wrong:M.cells.map(()=>false),time:0,done:false,auto:false};}
// ---------- archive ----------
function showArchive(){
  stopTimer();M=null;$('game').classList.add('hidden');$('archive').classList.remove('hidden');$('tools').style.visibility='hidden';$('puzTitle').textContent='';
  history.replaceState(null,'',location.pathname);
  const list=$('list');list.innerHTML='';
  for(const p of allPuzzles()){
    const st=store.get('p:'+p.id), n=p.grid.length, w=p.grid[0].length;
    const d=document.createElement('div');d.className='pcard';
    const mini=document.createElement('div');mini.className='mini';mini.style.gridTemplateColumns=`repeat(${w},1fr)`;
    let filled=0,tot=0;
    p.grid.join('').split('').forEach((ch,i)=>{const x=document.createElement('i');if(ch==='#'||ch==='.')x.className='b';else{tot++;if(st&&st.fill[i]){filled++;x.className='f';}}mini.appendChild(x)});
    const kind=n<=7?'Mini':n<=11?'Midi':'Daily';
    const status=st&&st.done?`<span class="st done">Solved · ${fmt(st.time)}</span>`:st&&filled?`<span class="st">${Math.round(100*filled/tot)}% · ${fmt(st.time)}</span>`:`<span class="st">Not started</span>`;
    d.innerHTML=`<div class="kind">${kind} · ${w}×${n}</div><div class="t"></div><div class="st by"></div>`;
    d.querySelector('.t').textContent=p.title;d.querySelector('.by').textContent=(p.author?'By '+p.author:'')+(p.source?' · '+p.source:'');
    d.prepend(mini);d.insertAdjacentHTML('beforeend',status);
    d.onclick=()=>openPuzzle(p.id);
    const rt=getRatings()[p.id];const rl=document.createElement('a');rl.className='rlink';rl.textContent=rt?'★'.repeat(rt.stars)+' · edit rating':'Rate';rl.onclick=e=>{e.stopPropagation();openRate(p);};d.appendChild(rl);list.appendChild(d);
  }
}
function fmt(s){s=s|0;const h=s/3600|0,m=(s%3600)/60|0,x=s%60;return (h?h+':'+String(m).padStart(2,'0'):m)+':'+String(x).padStart(2,'0');}
// ---------- game ----------
function openPuzzle(id){
  const p=allPuzzles().find(x=>x.id===id);if(!p)return showArchive();
  M=buildModel(p);S=store.get('p:'+id);if(!S||S.fill.length!==M.cells.length)S=fresh();
  history.replaceState(null,'','#'+encodeURIComponent(id));
  $('archive').classList.add('hidden');$('game').classList.remove('hidden');$('tools').style.visibility='visible';
  $('puzTitle').textContent=p.title+(p.author?'  ·  by '+p.author:'');
  const g=$('grid');g.innerHTML='';g.style.gridTemplateColumns=`repeat(${M.w},1fr)`;
  g.className='grid'+(M.w<=7?' small':M.w>=13?' big':'');
  M.cells.forEach((c,i)=>{const d=document.createElement('div');d.className='cell'+(c.blk?' blk':'');
    if(!c.blk){d.innerHTML=(c.num?`<span class="n">${c.num}</span>`:'')+'<span class="l"></span>';
      d.addEventListener('mousedown',e=>{e.preventDefault();clickCell(i)});}
    c.el=d;g.appendChild(d);});
  for(const d of ['across','down']){const ol=$(d+'List');ol.innerHTML='';
    for(const wd of M.words[d]){const li=document.createElement('li');li.innerHTML=`<b>${wd.num}</b><span></span>`;li.lastChild.textContent=wd.clue;
      li.onclick=()=>{dir=d;cur=firstEmpty(wd);render();focusIn();};wd.li=li;ol.appendChild(li);}}
  dir='across';cur=M.cells.findIndex(c=>!c.blk);const fw=M.words.across[0];if(fw)cur=firstEmpty(fw);
  paused=false;$('pauseOverlay').classList.add('hidden');
  document.querySelector('[data-act=autocheck]').classList.toggle('on',!!S.auto);
  render();if(!S.done)startTimer();else $('timer').textContent=fmt(S.time);focusIn();
}
function firstEmpty(wd){return wd.cells.find(i=>!S.fill[i])??wd.cells[0];}
function word(i=cur,d=dir){return M.cells[i][d]||M.cells[i][d==='across'?'down':'across'];}
function render(){
  if(!M)return;if(!M.cells[cur][dir])dir=dir==='across'?'down':'across';
  const wd=word(),other=M.cells[cur][dir==='across'?'down':'across'];
  M.cells.forEach((c,i)=>{if(c.blk)return;const e=c.el;
    e.classList.toggle('word',wd.cells.includes(i));e.classList.toggle('cur',i===cur);
    e.querySelector('.l').textContent=S.fill[i];
    e.classList.toggle('pencil',!!S.pen[i]&&!S.rev[i]);e.classList.toggle('revealed',!!S.rev[i]);
    const wrong=S.wrong[i]||(S.auto&&S.fill[i]&&S.fill[i]!==c.ans);e.classList.toggle('wrong',!!wrong&&S.fill[i]!==c.ans);});
  for(const d of ['across','down'])for(const w of M.words[d]){w.li.classList.toggle('active',w===wd);w.li.classList.toggle('cross',w===other);w.li.classList.toggle('filled',w.cells.every(i=>S.fill[i]));}
  wd.li.scrollIntoView({block:'nearest'});if(other)other.li.scrollIntoView({block:'nearest'});
  $('cbNum').textContent=wd.num+(wd.dir==='across'?'A':'D');$('cbText').textContent=wd.clue;
}
function clickCell(i){if(paused)return;if(i===cur)toggleDir();else{cur=i;if(!M.cells[i][dir])toggleDir(true);}render();focusIn();}
function toggleDir(noRender){const o=dir==='across'?'down':'across';if(M.cells[cur][o])dir=o;if(!noRender)render();}
function wordsInOrder(){return M.words.across.concat(M.words.down);}
function nextWord(back){const ws=wordsInOrder();let k=ws.indexOf(word());
  for(let t=0;t<ws.length;t++){k=(k+(back?-1:1)+ws.length)%ws.length;if(ws[k].cells.some(i=>!S.fill[i])||allFilled()){dir=ws[k].dir;cur=firstEmpty(ws[k]);return render();}}}
function allFilled(){return M.cells.every((c,i)=>c.blk||S.fill[i]);}
function move(dr,dc){const nd=dc?'across':'down';if(dir!==nd&&M.cells[cur][nd]){dir=nd;return render();}
  let r=M.cells[cur].r,c=M.cells[cur].c;for(;;){r+=dr;c+=dc;const x=M.at(r,c);if(!x)return;if(!x.blk){cur=r*M.w+c;return render();}}}
function advance(){const wd=word(),k=wd.cells.indexOf(cur);
  for(let j=k+1;j<wd.cells.length;j++)if(!S.fill[wd.cells[j]]){cur=wd.cells[j];return;}
  for(let j=0;j<k;j++)if(!S.fill[wd.cells[j]]){cur=wd.cells[j];return;}
  if(k<wd.cells.length-1&&!wd.cells.every(i=>S.fill[i])){cur=wd.cells[k+1];return;}
  if(wd.cells.every(i=>S.fill[i])&&!allFilled()){nextWord();return;}
  if(k<wd.cells.length-1)cur=wd.cells[k+1];}
function type(ch){if(S.done||paused)return;if(S.rev[cur]&&S.fill[cur]===M.cells[cur].ans){advance();return render();}
  S.fill[cur]=ch;S.pen[cur]=pencil;S.wrong[cur]=false;advance();render();save();checkSolved();}
function back(){if(S.done||paused)return;
  if(S.fill[cur]&&!S.rev[cur]){S.fill[cur]='';S.wrong[cur]=false;}
  else{const wd=word(),k=wd.cells.indexOf(cur);if(k>0)cur=wd.cells[k-1];else{const ws=wordsInOrder(),j=ws.indexOf(wd),pw=ws[(j-1+ws.length)%ws.length];dir=pw.dir;cur=pw.cells[pw.cells.length-1];}
    if(!S.rev[cur]){S.fill[cur]='';S.wrong[cur]=false;}}
  render();save();}
function checkSolved(){if(!allFilled())return;
  if(M.cells.every((c,i)=>c.blk||S.fill[i]===c.ans)){S.done=true;S.pen=S.pen.map(()=>false);stopTimer();save();render();
    $('mText').textContent=`You solved “${M.p.title}” in ${fmt(S.time)}.`+(S.rev.some(x=>x)?' (with some help)':'');rateUI($('rateBox'),M.p);$('modal').classList.remove('hidden');}
  else if(!S.warned){S.warned=true;$('rateBox').innerHTML='';$('mTitle').textContent='Almost there';$('mText').textContent='The grid is full, but at least one square is incorrect. Keep trying!';$('mClose').textContent='Keep trying';$('modal').classList.remove('hidden');}}
// ---------- check / reveal / clear ----------
function scope(s){return s==='cell'?[cur]:s==='word'?word().cells:M.cells.map((c,i)=>c.blk?-1:i).filter(i=>i>=0);}
function act(a){if(!M)return;const [k,s]=a.split('-');
  if(a==='autocheck'){S.auto=!S.auto;document.querySelector('[data-act=autocheck]').classList.toggle('on',S.auto);}
  else if(k==='check'){if(S.done)return;for(const i of scope(s))if(S.fill[i]&&S.fill[i]!==M.cells[i].ans)S.wrong[i]=true;}
  else if(k==='reveal'){if(S.done)return;for(const i of scope(s))if(S.fill[i]!==M.cells[i].ans){S.fill[i]=M.cells[i].ans;S.rev[i]=true;S.wrong[i]=false;S.pen[i]=false;}checkSolved();}
  else if(k==='clear'){if(s==='all'){S=fresh();startTimer();}
    else{const idx=s==='incomplete'?scope('puzzle').filter(i=>S.fill[i]!==M.cells[i].ans||!S.wrong):scope(s==='word'?'word':'puzzle');
      for(const i of idx){if(s==='incomplete'&&S.fill[i]&&!S.wrong[i]&&!(S.auto&&S.fill[i]!==M.cells[i].ans))continue;if(S.rev[i]&&S.fill[i]===M.cells[i].ans&&s!=='puzzle')continue;S.fill[i]='';S.wrong[i]=false;S.rev[i]=false;S.pen[i]=false;}
      if(s==='puzzle'){S.done=false;S.warned=false;startTimer();}}}
  save();render();}
// ---------- timer ----------
function startTimer(){stopTimer();$('timer').textContent=fmt(S.time);timerH=setInterval(()=>{if(paused||document.hidden||!S||S.done)return;S.time++;$('timer').textContent=fmt(S.time);if(S.time%5===0)save();},1000);}
function stopTimer(){if(timerH)clearInterval(timerH);timerH=null;}
function setPause(v){paused=v;$('pauseOverlay').classList.toggle('hidden',!v);$('grid').style.visibility=v?'hidden':'visible';save();}
// ---------- input ----------
const isTouch=matchMedia('(pointer:coarse)').matches||window.innerWidth<=820;
function focusIn(){if(!isTouch)$('hiddenInput').focus({preventScroll:true});}
document.addEventListener('keydown',e=>{
  if(!M||$('game').classList.contains('hidden')||!$('modal').classList.contains('hidden'))return;
  if(e.metaKey||e.ctrlKey||e.altKey)return;const k=e.key;
  if(/^[a-zA-Z0-9]$/.test(k)){e.preventDefault();type(k.toUpperCase());}
  else if(k==='Backspace'||k==='Delete'){e.preventDefault();back();}
  else if(k==='ArrowLeft'){e.preventDefault();move(0,-1);}else if(k==='ArrowRight'){e.preventDefault();move(0,1);}
  else if(k==='ArrowUp'){e.preventDefault();move(-1,0);}else if(k==='ArrowDown'){e.preventDefault();move(1,0);}
  else if(k==='Tab'||k==='Enter'){e.preventDefault();nextWord(e.shiftKey);}
  else if(k===' '){e.preventDefault();toggleDir();}
  else if(k==='.'){pencil=!pencil;$('pencilBtn').classList.toggle('on',pencil);}
});
function buildKbd(){const rows=['QWERTYUIOP','ASDFGHJKL','⇄ZXCVBNM⌫'];const k=$('kbd');
  rows.forEach(r=>{const d=document.createElement('div');d.className='row';
    for(const ch of r){const b=document.createElement('button');b.textContent=ch;if(ch==='⌫'||ch==='⇄')b.className='wide';
      b.addEventListener('pointerdown',e=>{e.preventDefault();if(!M)return;if(ch==='⌫')back();else if(ch==='⇄')toggleDir();else type(ch);});d.appendChild(b);}
    k.appendChild(d);});}
$('cluebar').addEventListener('click',()=>toggleDir());
$('pencilBtn').onclick=()=>{pencil=!pencil;$('pencilBtn').classList.toggle('on',pencil);focusIn();};
$('pauseBtn').onclick=()=>{if(M&&!S.done)setPause(!paused);};$('resumeBtn').onclick=()=>{setPause(false);focusIn();};
$('homeBtn').onclick=()=>{save();showArchive();};
document.querySelectorAll('.menu').forEach(m=>m.querySelector('button').onclick=e=>{e.stopPropagation();const o=m.classList.contains('open');document.querySelectorAll('.menu').forEach(x=>x.classList.remove('open'));if(!o)m.classList.add('open');});
document.addEventListener('click',()=>document.querySelectorAll('.menu').forEach(x=>x.classList.remove('open')));
document.querySelectorAll('.dd a').forEach(a=>a.onclick=()=>{act(a.dataset.act);focusIn();});
$('mClose').onclick=()=>{$('modal').classList.add('hidden');$('mTitle').textContent='Congratulations!';$('mClose').textContent='Admire puzzle';focusIn();};
$('mArchive').onclick=()=>{$('modal').classList.add('hidden');$('mTitle').textContent='Congratulations!';showArchive();};
window.addEventListener('beforeunload',save);
$('fileIn').onchange=async e=>{const f=e.target.files[0];if(!f)return;
  try{const p=await importFile(f);const im=(store.get('imported')||[]).filter(x=>x.id!==p.id);im.push(p);store.set('imported',im);$('importMsg').textContent='Loaded “'+p.title+'”.';showArchive();openPuzzle(p.id);}
  catch(err){$('importMsg').textContent='Could not read file: '+err.message;}e.target.value='';};

// ---------- ratings ----------
const TAGS=['fun','great theme','clever clues','smooth fill','too easy','too hard','obscure fill','boring clues','weak theme'];
function getRatings(){return store.get('ratings')||{};}
function puzzleMeta(p){const m=p.meta||{};return {title:p.title,size:p.grid[0].length+'x'+p.grid.length,difficulty:m.difficulty||'unknown',themeType:m.themeType||'unknown',clueStyle:m.clueStyle||'unknown',wordCount:m.wordCount||null,source:p.source||'original'};}
function rateUI(box,p){const R=getRatings(),prev=R[p.id]||{};let stars=prev.stars||0;const tags=new Set(prev.tags||[]);
  box.innerHTML='<div class="stars"></div><div class="tags"></div><textarea maxlength="500" placeholder="Short note (optional)"></textarea><button class="save">Save rating</button><div class="ok"></div>';
  const st=box.querySelector('.stars');for(let i=1;i<=5;i++){const s=document.createElement('span');s.textContent='★';s.title=i+' star'+(i>1?'s':'');s.onclick=()=>{stars=i;paint();};st.appendChild(s);}
  const paint=()=>[...st.children].forEach((s,i)=>s.classList.toggle('on',i<stars));paint();
  const tg=box.querySelector('.tags');for(const t of TAGS){const s=document.createElement('span');s.textContent=t;s.classList.toggle('on',tags.has(t));s.onclick=()=>{tags.has(t)?tags.delete(t):tags.add(t);s.classList.toggle('on');};tg.appendChild(s);}
  const ta=box.querySelector('textarea');ta.value=prev.note||'';ta.addEventListener('keydown',e=>e.stopPropagation());
  box.querySelector('.save').onclick=()=>{if(!stars){box.querySelector('.ok').textContent='Pick 1–5 stars first.';return;}
    const ps=store.get('p:'+p.id)||{};const R2=getRatings();
    R2[p.id]={puzzleId:p.id,stars,tags:[...tags],note:ta.value.trim(),ratedAt:new Date().toISOString(),solved:!!ps.done,solveTimeSec:ps.time??null,usedReveal:!!(ps.rev&&ps.rev.some(x=>x)),meta:puzzleMeta(p)};
    store.set('ratings',R2);box.querySelector('.ok').textContent='Thanks! Rating saved.';updCount();};}
function openRate(p){$('rTitle').textContent='Rate “'+p.title+'”';rateUI($('rateBox2'),p);$('rmodal').classList.remove('hidden');}
$('rCancel').onclick=()=>{$('rmodal').classList.add('hidden');if(!M)showArchive();};
function updCount(){const n=Object.keys(getRatings()).length;$('rCount').textContent=n+' rated';}
$('exportBtn').onclick=()=>{const data={schema:'crosser-ratings/1',exportedAt:new Date().toISOString(),ratings:Object.values(getRatings()),puzzles:allPuzzles().map(p=>Object.assign({id:p.id},puzzleMeta(p)))};
  const b=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='ratings.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);};
buildKbd();updCount();
const h=decodeURIComponent(location.hash.slice(1));if(h&&allPuzzles().some(p=>p.id===h))openPuzzle(h);else showArchive();
