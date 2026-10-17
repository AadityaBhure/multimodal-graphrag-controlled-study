"""Interactive SVG view of a small graph with a precomputed, deterministic layout (built by the bundle builder).

Input: {'nodes': [{id, label, type, x, y, gold?, answer?, seed?, anchor?, witness?}], 'edges': [{s, t, rel, edge, witness?}],
'total_nodes', 'total_edges', 'shown_nodes', 'shown_edges'}. Labels are corpus data; they are JSON-encoded and escaped
in the page, never interpreted as HTML.
"""
import json
import streamlit as st

FLAG_TEXT = {'gold': 'correct answer', 'answer': 'returned by the model', 'seed': 'retriever seed', 'anchor': 'named in the question',
             'witness': 'on the path that proves the answer'}


def caption(g):
    if g['shown_nodes'] < g['total_nodes'] or g['shown_edges'] < g['total_edges']:
        return 'Showing %d of %d nodes and %d of %d relations (display limit only).' % (g['shown_nodes'], g['total_nodes'], g['shown_edges'], g['total_edges'])
    return '%d nodes and %d relations.' % (g['total_nodes'], g['total_edges'])


def render(g, height=500, key=None):
    if not g['nodes']:
        st.info('No graph evidence to show.')
        return
    data = json.dumps(g, ensure_ascii=False, sort_keys=True).replace('</', '<\\/')
    st.iframe(_TEMPLATE.replace('__DATA__', data).replace('__H__', str(height)), height=height + 96)


_TEMPLATE = r"""<!doctype html><html><head><meta charset="utf-8"><style>
body{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#1f2937}
.bar{display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin:2px 0 6px 0}
button{border:1px solid #cbd5e1;background:#fff;border-radius:6px;padding:2px 10px;cursor:pointer;font-size:13px}
button:hover{background:#f1f5f9}
label{font-size:13px;color:#334155}
svg{box-sizing:border-box;width:100%;height:__H__px;background:#fff;border:1px solid #e2e8f0;border-radius:10px;cursor:grab;touch-action:none;display:block}
.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:12.5px;margin-top:6px;align-items:center;color:#334155}
.legend span{display:inline-flex;gap:5px;align-items:center}
#tip{position:fixed;pointer-events:none;background:#0f172a;color:#fff;font-size:12px;padding:6px 9px;border-radius:6px;max-width:340px;display:none;z-index:9;line-height:1.35}
#sel{font-size:13px;margin-top:4px;min-height:18px;color:#334155}
text{font-size:12px;pointer-events:none;paint-order:stroke;stroke:#fff;stroke-width:3px;stroke-linejoin:round}
</style></head><body>
<div class="bar"><button id="fit">Fit</button><button id="zin">+</button><button id="zout">−</button>
<label><input type="checkbox" id="elab" checked> relation labels</label><label><input type="checkbox" id="nlab" checked> node names</label></div>
<svg id="svg" viewBox="0 0 900 __H__" preserveAspectRatio="xMidYMid meet">
<defs><marker id="arr" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="8" markerHeight="8" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#475569"/></marker>
<marker id="arrw" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="8" markerHeight="8" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#15803d"/></marker></defs>
<g id="vp"><g id="edges"></g><g id="nodes"></g></g></svg>
<div class="legend" id="legend"></div><div id="sel">Hover a node or relation for details; click to keep it here.</div><div id="tip"></div>
<script>
(function(){
const G=__DATA__, NS='http://www.w3.org/2000/svg', H=__H__;
const COLORS={paper:'#3b82f6',author:'#f59e0b',institution:'#10b981',field_of_study:'#a855f7'};
const NAMES={paper:'Paper',author:'Author',institution:'Institution',field_of_study:'Field of study'};
const LET={paper:'P',author:'A',institution:'I',field_of_study:'F'};
const RELTXT={WRITES:'writes',AFFILIATED_WITH:'affiliated with',CITES:'cites',HAS_TOPIC:'has topic'};
const FLAGS={gold:['#16a34a','correct answer'],answer:['#2563eb','returned by the model'],seed:['#db2777','retriever seed'],anchor:['#ea580c','named in the question'],witness:['#15803d','on the proving path']};
const svg=document.getElementById('svg'),vp=document.getElementById('vp'),tip=document.getElementById('tip'),sel=document.getElementById('sel');
let sc=1,tx=0,ty=0;function apply(){vp.setAttribute('transform','translate('+tx+','+ty+') scale('+sc+')');}
function el(n,a,p){const x=document.createElementNS(NS,n);for(const k in a)x.setAttribute(k,a[k]);if(p)p.appendChild(x);return x;}
function esc(s){return String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
function shape(t,x,y,r,g,ex){
 if(t==='paper')return el('circle',Object.assign({cx:x,cy:y,r:r},ex),g);
 if(t==='author')return el('polygon',Object.assign({points:[[x,y-r*1.25],[x+r*1.25,y],[x,y+r*1.25],[x-r*1.25,y]].map(p=>p.join(',')).join(' ')},ex),g);
 if(t==='institution'){const p=[];for(let i=0;i<6;i++){const a=Math.PI/3*i;p.push((x+r*1.15*Math.cos(a))+','+(y+r*1.15*Math.sin(a)));}return el('polygon',Object.assign({points:p.join(' ')},ex),g);}
 return el('rect',Object.assign({x:x-r*1.1,y:y-r*.85,width:r*2.2,height:r*1.7,rx:5},ex),g);}
const by={};G.nodes.forEach(n=>by[n.id]=n);
const eg=document.getElementById('edges'),ng=document.getElementById('nodes'),elabels=[],nlabels=[];
G.edges.forEach(e=>{const a=by[e.s],b=by[e.t];if(!a||!b)return;
 const dx=b.x-a.x,dy=b.y-a.y,len=Math.hypot(dx,dy)||1,ux=dx/len,uy=dy/len,w=!!e.witness;
 el('line',{x1:a.x+ux*20,y1:a.y+uy*20,x2:b.x-ux*24,y2:b.y-uy*24,stroke:w?'#15803d':'#64748b','stroke-width':w?3.6:1.8,'marker-end':w?'url(#arrw)':'url(#arr)'},eg);
 const hit=el('line',{x1:a.x,y1:a.y,x2:b.x,y2:b.y,stroke:'transparent','stroke-width':12},eg);
 const t=el('text',{x:(a.x+b.x)/2,y:(a.y+b.y)/2-6,'text-anchor':'middle',fill:w?'#14532d':'#334155','font-weight':600},eg);t.textContent=RELTXT[e.rel]||e.rel;elabels.push(t);
 const info=esc(a.label)+' <b>'+(RELTXT[e.rel]||e.rel)+'</b> '+esc(b.label)+(w?'<br>on the path that proves the answer':'');
 hit.addEventListener('mousemove',ev=>show(ev,info));hit.addEventListener('mouseleave',()=>tip.style.display='none');hit.addEventListener('click',()=>{sel.innerHTML=info;});});
function wrap(t){t=String(t);if(t.length<=24)return [t];let i=t.lastIndexOf(' ',24);if(i<8)i=24;let a=t.slice(0,i).trim(),b=t.slice(i).trim();if(b.length>24)b=b.slice(0,23)+'…';return [a,b];}
G.nodes.forEach(n=>{const g=el('g',{style:'cursor:pointer'},ng);let r=22;
 ['gold','answer','anchor','seed'].forEach(f=>{if(n[f]){shape(n.type,n.x,n.y,r,g,{fill:'none',stroke:FLAGS[f][0],'stroke-width':f==='seed'?2.2:3.6,'stroke-dasharray':f==='seed'?'4 3':'none'});r+=5;}});
 shape(n.type,n.x,n.y,15,g,{fill:COLORS[n.type]||'#64748b',stroke:'#0f172a','stroke-width':1.2});
 const l=el('text',{x:n.x,y:n.y+4,'text-anchor':'middle',fill:'#fff','font-weight':700,style:'stroke:none'},g);l.textContent=LET[n.type]||'?';
 const lab=el('text',{x:n.x,y:n.y+r+12,'text-anchor':'middle',fill:'#0f172a'},g);wrap(n.label).forEach((ln,i)=>{const s=el('tspan',{x:n.x,dy:i?'1.15em':'0'},lab);s.textContent=ln;});nlabels.push(lab);
 const flags=Object.keys(FLAGS).filter(f=>n[f]).map(f=>FLAGS[f][1]).join(', ');
 const info='<b>'+(NAMES[n.type]||'Node')+'</b>'+(flags?' · '+flags:'')+'<br>'+esc(n.label)+'<br><span style="opacity:.75">stark:'+n.id+'</span>';
 g.addEventListener('mousemove',ev=>show(ev,info));g.addEventListener('mouseleave',()=>tip.style.display='none');g.addEventListener('click',()=>{sel.innerHTML=info;});});
function show(ev,h){tip.innerHTML=h;tip.style.display='block';tip.style.left=Math.min(window.innerWidth-350,ev.clientX+14)+'px';tip.style.top=(ev.clientY+14)+'px';}
function fit(){const xs=G.nodes.map(n=>n.x),ys=G.nodes.map(n=>n.y),x0=Math.min(...xs)-70,x1=Math.max(...xs)+70,y0=Math.min(...ys)-50,y1=Math.max(...ys)+70;
 sc=Math.min(900/(x1-x0),H/(y1-y0),2.0);tx=450-sc*(x0+x1)/2;ty=H/2-sc*(y0+y1)/2;apply();}
function zoomAt(f,cx,cy){const nx=(cx-tx)/sc,ny=(cy-ty)/sc;sc=Math.max(.15,Math.min(6,sc*f));tx=cx-nx*sc;ty=cy-ny*sc;apply();}
document.getElementById('fit').onclick=fit;document.getElementById('zin').onclick=()=>zoomAt(1.25,450,H/2);document.getElementById('zout').onclick=()=>zoomAt(.8,450,H/2);
document.getElementById('elab').onchange=ev=>elabels.forEach(t=>t.style.display=ev.target.checked?'':'none');
document.getElementById('nlab').onchange=ev=>nlabels.forEach(t=>t.style.display=ev.target.checked?'':'none');
svg.addEventListener('wheel',ev=>{ev.preventDefault();const r=svg.getBoundingClientRect();zoomAt(ev.deltaY<0?1.12:.89,(ev.clientX-r.left)*900/r.width,(ev.clientY-r.top)*H/r.height);},{passive:false});
let drag=null;svg.addEventListener('pointerdown',ev=>{drag={x:ev.clientX,y:ev.clientY,tx:tx,ty:ty};svg.setPointerCapture(ev.pointerId);svg.style.cursor='grabbing';});
svg.addEventListener('pointermove',ev=>{if(!drag)return;const r=svg.getBoundingClientRect();tx=drag.tx+(ev.clientX-drag.x)*900/r.width;ty=drag.ty+(ev.clientY-drag.y)*H/r.height;apply();});
svg.addEventListener('pointerup',()=>{drag=null;svg.style.cursor='grab';});
const lg=document.getElementById('legend');const used=new Set(G.nodes.map(n=>n.type));
Object.keys(COLORS).filter(t=>used.has(t)).forEach(t=>{const s=document.createElement('span');const v=document.createElementNS(NS,'svg');v.setAttribute('width',18);v.setAttribute('height',18);v.style.cssText='width:18px;height:18px;border:none;cursor:default';shape(t,9,9,6,v,{fill:COLORS[t],stroke:'#0f172a'});s.appendChild(v);s.appendChild(document.createTextNode(NAMES[t]));lg.appendChild(s);});
Object.keys(FLAGS).filter(f=>G.nodes.some(n=>n[f])).forEach(f=>{lg.insertAdjacentHTML('beforeend','<span><svg width="18" height="18" style="width:18px;height:18px;border:none"><circle cx="9" cy="9" r="7" fill="none" stroke="'+FLAGS[f][0]+'" stroke-width="'+(f==='seed'?2:3)+'"'+(f==='seed'?' stroke-dasharray="3 2"':'')+'/></svg>'+FLAGS[f][1]+'</span>');});
lg.insertAdjacentHTML('beforeend','<span style="color:#64748b">arrows follow the relation direction</span>');
fit();})();
</script></body></html>"""
