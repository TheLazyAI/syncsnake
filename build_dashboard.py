#!/usr/bin/env python3
"""Build dashboard.html by injecting catalogue.json into the template."""
import json, os, sys

base = os.path.dirname(os.path.abspath(__file__))
cat  = json.load(open(os.path.join(base, 'catalogue.json')))

HTML = r"""<!DOCTYPE html>
<html class="dark" lang="en">
<head>
<meta charset="utf-8"/>
<meta content="width=device-width,initial-scale=1.0" name="viewport"/>
<title>SyncSnake | Agency Rolodex</title>
<meta name="description" content="SyncSnake sync licensing intelligence — 332 verified opportunities for independent artists."/>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet"/>
<script>
tailwind.config={darkMode:"class",theme:{extend:{colors:{
  "primary":"#22d3ee","on-primary":"#00363e",
  "secondary":"#aa0266","on-secondary":"#ffbad3",
  "background":"#0b1326","surface":"#0b1326",
  "surface-lowest":"#060e20","surface-low":"#131b2e",
  "surface-container":"#171f33","surface-variant":"#2d3449",
  "outline":"#859397","outline-variant":"#3c494c",
  "on-surface":"#dae2fd","on-surface-variant":"#bbc9cd"
}}}}
</script>
<style>
*,*::before,*::after{box-sizing:border-box}
body{
  background:#0b1326;
  background-image:radial-gradient(circle at 8% 15%,rgba(34,211,238,.06) 0%,transparent 48%),
    radial-gradient(circle at 92% 85%,rgba(170,2,102,.06) 0%,transparent 48%);
  background-attachment:fixed;
  color:#dae2fd;
  font-family:'Inter',sans-serif;
  overflow-x:hidden;
  user-select:none;
}
h1,h2,h3{font-family:'Plus Jakarta Sans',sans-serif}
.sc::-webkit-scrollbar{width:5px}
.sc::-webkit-scrollbar-track{background:transparent}
.sc::-webkit-scrollbar-thumb{background:#2d3449;border-radius:10px}
.glass{background:rgba(23,31,51,.65);backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px);border:1px solid rgba(133,147,151,.12)}
.nav-item{display:flex;align-items:center;gap:10px;padding:9px 13px;border-radius:10px;font-size:13px;font-weight:500;color:#859397;cursor:pointer;transition:background .15s,color .15s;border-left:3px solid transparent;margin-bottom:2px}
.nav-item:hover{background:rgba(45,52,73,.55);color:#dae2fd}
.nav-item.active{background:rgba(34,211,238,.07);color:#22d3ee;border-left-color:#22d3ee;font-weight:700}
.nav-item .nc{margin-left:auto;font-size:10px;font-weight:700;background:#2d3449;color:#859397;padding:2px 7px;border-radius:999px}
.nav-item.active .nc{background:rgba(34,211,238,.15);color:#22d3ee}

/* ══════════════════════════════════════════════════════════
   3D CARD STACK  — "looking down at a deck of cards"
   
   How it works:
   - perspective-origin is set ABOVE the scene center
   - viewer looks DOWN at the card stack
   - active card at z=0 shows fully, facing up
   - cards behind (z < 0) appear HIGHER on screen and SMALLER
     because they're further from the eye (toward vanishing point)
   - the trapezoidal narrowing happens automatically from CSS perspective
   - NO rotateX on cards needed — translateZ alone creates the effect
   - NO carousel rotation — individual card z-positions drive everything
   ══════════════════════════════════════════════════════════ */
.scene{
  width:100%;
  perspective:900px;
  perspective-origin:50% -55%;   /* vanishing point above — creates downward-looking view */
  position:relative;
  display:flex;
  align-items:center;
  justify-content:center;
  overflow:hidden;
}
.card-stage{
  /* The 3D container — preserve-3d propagates perspective to children */
  position:relative;
  width:min(620px,82vw);
  height:min(420px,56vh);
  transform-style:preserve-3d;
  flex-shrink:0;
}
.rolo-card{
  position:absolute;
  inset:0;
  border-radius:18px;
  padding:28px 30px;
  display:flex;flex-direction:column;
  backface-visibility:hidden;
  will-change:transform;
  /* NO transform-origin override — default 50% 50% */
  box-shadow:0 24px 80px rgba(0,0,0,.85);
  border:2px solid #3c494c;
  cursor:pointer;
}
/* Card colour cycle */
.cd{background:#171f33;color:#dae2fd;border-color:#3c494c}
.cl{background:#dae2fd;color:#0b1326;border-color:rgba(0,0,0,.08)}
.ca{background:#aa0266;color:#fff;border-color:rgba(255,255,255,.18)}

/* State filters — opacity & zIndex set by JS */
.rolo-card[data-s="active"]{ filter:none;           pointer-events:auto  }
.rolo-card[data-s="behind"]{ filter:brightness(.52); pointer-events:none  }
.rolo-card[data-s="gone"]  { filter:brightness(.1);  pointer-events:none  }
.rolo-card[data-s="hidden"]{ opacity:0!important;    pointer-events:none  }

/* Spine — visual hinge bar sits at bottom of card-stage */
.spine{
  position:absolute;
  width:calc(min(620px,82vw) + 40px);
  height:8px;
  /* align with bottom of card-stage center */
  background:linear-gradient(90deg,transparent,#4a5568 10%,#8899a6 50%,#4a5568 90%,transparent);
  border-radius:4px;
  box-shadow:0 2px 14px rgba(0,0,0,.9),0 0 18px rgba(34,211,238,.07);
  border-top:1px solid rgba(255,255,255,.09);
  z-index:300;
}

/* Dots */
#ndots{display:flex;align-items:center;gap:5px}
#ndots .d{width:6px;height:6px;border-radius:999px;background:rgba(60,73,76,.65);transition:all .28s}
#ndots .d.on{width:20px;background:#22d3ee;box-shadow:0 0 8px rgba(34,211,238,.4)}

/* View toggle */
.vtog{background:#060e20;border:1px solid #3c494c;border-radius:999px;padding:4px;display:inline-flex;position:relative;cursor:pointer}
.vpill{position:absolute;top:4px;bottom:4px;width:calc(50% - 4px);background:#2d3449;border-radius:999px;transition:transform .28s cubic-bezier(.2,.8,.2,1)}
.vopt{position:relative;z-index:1;padding:6px 18px;font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:#859397;transition:color .22s}
.vopt.on{color:#22d3ee}
.vtog[data-v="grid"] .vpill{transform:translateX(100%)}

/* Bento */
.bento{background:#171f33;border:1px solid rgba(60,73,76,.55);border-radius:14px;padding:18px;display:flex;flex-direction:column;gap:9px;transition:transform .2s,border-color .2s,box-shadow .2s;cursor:pointer}
.bento:hover{transform:translateY(-3px);border-color:rgba(34,211,238,.28);box-shadow:0 10px 28px rgba(0,0,0,.28)}

/* Agent dots */
@keyframes ap{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.45;transform:scale(.75)}}
.adot{animation:ap 1.6s ease-in-out infinite}
.adot:nth-child(2){animation-delay:.18s}.adot:nth-child(3){animation-delay:.36s}
.adot:nth-child(4){animation-delay:.54s}.adot:nth-child(5){animation-delay:.72s}
.adot:nth-child(6){animation-delay:.9s}.adot:nth-child(7){animation-delay:1.08s}
.adot:nth-child(8){animation-delay:1.26s}.adot:nth-child(9){animation-delay:1.44s}

.gdots{background-image:radial-gradient(circle,rgba(60,73,76,.4) 1px,transparent 1px);background-size:30px 30px}
.btac{transition:transform .16s,filter .16s}
.btac:hover{transform:translateY(-2px);filter:brightness(1.1)}
.btac:active{transform:translateY(1px)}
</style>
</head>
<body class="flex min-h-screen">

<!-- SIDEBAR -->
<aside class="w-[268px] h-screen fixed left-0 top-0 glass border-r border-outline-variant/20 flex flex-col py-5 z-50 overflow-hidden">
  <div class="px-5 mb-6 flex items-center gap-3 flex-shrink-0">
    <div class="w-10 h-10 rounded-xl flex items-center justify-center font-black text-xl"
         style="background:linear-gradient(135deg,#aa0266,#22d3ee);box-shadow:0 0 18px rgba(34,211,238,.22)">🐍</div>
    <div>
      <div class="text-[17px] font-black text-on-surface tracking-tight leading-none">SyncSnake</div>
      <div class="text-[9px] font-bold tracking-[.18em] text-outline uppercase mt-0.5">Medusa Agent ◆ v2.0</div>
    </div>
  </div>
  <div class="mx-4 mb-5 bg-surface-lowest/80 rounded-xl p-3 border border-outline-variant/30 flex-shrink-0">
    <div class="flex items-center justify-between mb-2">
      <span class="text-[9px] font-black tracking-[.2em] text-outline uppercase">Agent Network</span>
      <span class="text-[9px] font-bold text-primary bg-primary/10 px-2 py-0.5 rounded-full">9/9 ACTIVE</span>
    </div>
    <div class="flex gap-1.5">
      <div class="adot w-2 h-2 rounded-full bg-primary"></div><div class="adot w-2 h-2 rounded-full bg-primary"></div>
      <div class="adot w-2 h-2 rounded-full bg-primary"></div><div class="adot w-2 h-2 rounded-full bg-primary"></div>
      <div class="adot w-2 h-2 rounded-full bg-primary"></div><div class="adot w-2 h-2 rounded-full bg-primary"></div>
      <div class="adot w-2 h-2 rounded-full bg-primary"></div><div class="adot w-2 h-2 rounded-full bg-primary"></div>
      <div class="adot w-2 h-2 rounded-full bg-primary"></div>
    </div>
    <div class="text-[9px] text-outline/60 mt-2 font-mono">Last sync: just now · Google Search grounded</div>
  </div>
  <div class="px-5 mb-1 flex-shrink-0">
    <p class="text-[9px] font-black tracking-[.22em] text-outline uppercase">Data Categories</p>
  </div>
  <nav class="flex-1 sc overflow-y-auto px-3" id="nav"></nav>
  <div class="mt-auto px-4 pt-4 border-t border-outline-variant/20 flex-shrink-0">
    <div class="text-[9px] text-outline/45 text-center"><span class="text-primary/65 font-bold">SyncSnake</span> · <span class="text-on-surface/55 font-bold">Medusa</span> 🐍</div>
  </div>
</aside>

<!-- MAIN -->
<main class="ml-[268px] flex-1 flex flex-col min-h-screen">
  <header class="h-[68px] px-7 flex justify-between items-center sticky top-0 z-40 border-b border-outline-variant/20"
          style="background:rgba(11,19,38,.88);backdrop-filter:blur(20px)">
    <div class="flex items-center gap-4">
      <h1 id="htitle" class="text-2xl font-black text-on-surface tracking-tight">Agencies</h1>
      <div class="bg-surface-container rounded-full px-3 py-1 flex items-center gap-2 border border-outline-variant/25">
        <span class="w-2 h-2 rounded-full bg-primary animate-pulse"></span>
        <span id="hcount" class="text-[10px] font-bold text-outline uppercase tracking-wider">—</span>
      </div>
    </div>
    <div class="flex items-center gap-5">
      <div class="vtog" id="vtog" data-v="card" onclick="toggleView()">
        <div class="vpill"></div>
        <div class="vopt on" id="vs">Showcase</div>
        <div class="vopt" id="vg">Grid</div>
      </div>
      <span class="material-symbols-outlined text-outline hover:text-primary transition-colors cursor-pointer text-[22px]" onclick="openMap()">satellite_alt</span>
    </div>
  </header>

  <!-- SHOWCASE -->
  <section id="showcase" class="flex-1 flex flex-col relative overflow-hidden" style="cursor:grab">
    <div class="absolute inset-0 gdots pointer-events-none"></div>

    <!-- 3D Scene -->
    <div class="scene flex-1" id="scene">
      <!-- card-stage is the 3D preserve-3d container -->
      <div class="card-stage" id="cardStage">
        <!-- cards injected here by JS -->
      </div>
      <!-- Spine sits below the card-stage, aligned by JS -->
      <div class="spine" id="spine"></div>
    </div>

    <!-- Nav dots -->
    <div class="absolute bottom-9 flex flex-col items-center gap-3 z-30 pointer-events-none left-0 right-0">
      <div id="ndots" class="pointer-events-auto"></div>
      <div class="flex items-center gap-2 text-[10px] font-bold tracking-widest uppercase text-outline/45">
        <span class="material-symbols-outlined text-[14px]">swipe_vertical</span>Scroll · drag · ↑↓
      </div>
    </div>

    <!-- Arrow buttons -->
    <div class="absolute inset-x-8 top-1/2 -translate-y-1/2 flex justify-between pointer-events-none z-[400]">
      <button class="w-[52px] h-[52px] rounded-full glass flex items-center justify-center text-primary pointer-events-auto btac hover:bg-primary hover:text-on-primary shadow-lg" onclick="step(-1)">
        <span class="material-symbols-outlined text-[28px]">expand_less</span>
      </button>
      <button class="w-[52px] h-[52px] rounded-full glass flex items-center justify-center text-primary pointer-events-auto btac hover:bg-primary hover:text-on-primary shadow-lg" onclick="step(1)">
        <span class="material-symbols-outlined text-[28px]">expand_more</span>
      </button>
    </div>
    <div class="absolute top-4 right-6 z-30 text-[11px] font-bold text-outline/55 font-mono" id="counter">— / —</div>
  </section>

  <!-- GRID VIEW -->
  <section id="gridview" class="hidden flex-1 p-7 overflow-y-auto sc">
    <div class="flex justify-between items-end mb-7">
      <div>
        <h2 id="gtitle" class="text-3xl font-black text-on-surface tracking-tight mb-1">Grid</h2>
        <p class="text-outline text-sm">All records</p>
      </div>
      <div class="relative w-[272px]">
        <span class="material-symbols-outlined absolute left-3.5 top-1/2 -translate-y-1/2 text-outline text-[17px]">search</span>
        <input id="srch" type="text" class="w-full bg-surface-lowest border border-outline-variant/45 rounded-xl py-3 pl-10 pr-4 text-sm text-on-surface placeholder-outline/45 focus:outline-none focus:border-primary transition-all" placeholder="Filter…" oninput="filterGrid(this.value)">
      </div>
    </div>
    <div class="glass rounded-2xl p-5"><div class="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4" id="grid"></div></div>
  </section>
</main>

<!-- AGENT MAP MODAL -->
<div id="mapmodal" class="hidden fixed inset-0 bg-background/90 z-[2000] backdrop-blur-lg items-center justify-center">
  <div class="bg-surface-lowest border border-outline-variant/35 rounded-3xl p-6 shadow-2xl max-w-2xl w-full mx-4 relative overflow-hidden">
    <div class="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-primary to-secondary"></div>
    <div class="flex justify-between items-center mb-5">
      <h2 class="text-sm font-black tracking-[.18em] uppercase flex items-center gap-2">
        <span class="material-symbols-outlined text-primary text-[17px]">satellite_alt</span>Medusa · SyncSnake Agent Network
      </h2>
      <button onclick="closeMap()" class="w-9 h-9 rounded-full bg-surface-variant flex items-center justify-center text-outline hover:text-white hover:bg-secondary transition-colors btac">
        <span class="material-symbols-outlined text-[17px]">close</span>
      </button>
    </div>
    <div class="bg-[#040810] border border-outline-variant/22 rounded-xl overflow-hidden h-[380px]">
      <canvas id="acanvas" class="w-full h-full"></canvas>
    </div>
    <div class="mt-4 grid grid-cols-3 gap-3 text-center">
      <div class="bg-surface-container rounded-xl p-3"><div class="text-2xl font-black text-primary" id="mtotal">0</div><div class="text-[10px] text-outline uppercase tracking-wider mt-1">Total Records</div></div>
      <div class="bg-surface-container rounded-xl p-3"><div class="text-2xl font-black">9</div><div class="text-[10px] text-outline uppercase tracking-wider mt-1">Agents</div></div>
      <div class="bg-surface-container rounded-xl p-3"><div class="text-2xl font-black text-secondary">10</div><div class="text-[10px] text-outline uppercase tracking-wider mt-1">Categories</div></div>
    </div>
  </div>
</div>

<script>
// ══ DATA ══════════════════════════════════════════════════════════════
const CAT = CATALOGUE_JSON_PLACEHOLDER;

const CATS = [
  {key:"agencies",     label:"Sync Agencies",    icon:"folder_special",
   T:r=>r.name, S:r=>r.location||"", M:r=>r.website||"", B:r=>r.submission_guidelines||"", C:r=>r.contact_info||""},
  {key:"supervisors",  label:"Music Supervisors", icon:"groups",
   T:r=>r.name, S:r=>r.company||"", M:r=>r.location||"", B:r=>r.submission_policy||r.notable_projects||"", C:r=>r.contact_info||""},
  {key:"platforms",    label:"Brief Platforms",   icon:"assignment",
   T:r=>r.name, S:r=>r.url||"", M:r=>"", B:r=>r.description||"", C:r=>r.requirements||""},
  {key:"music_libraries",label:"Music Libraries", icon:"library_music",
   T:r=>r.name, S:r=>r.payout_model||"", M:r=>r.submission_status||"", B:r=>r.requirements_genres||"", C:r=>r.url||""},
  {key:"grants",       label:"Grants & Funding",  icon:"payments",
   T:r=>r.name, S:r=>r.organization||"", M:r=>r.deadlines||"", B:r=>r.eligibility_summary||"", C:r=>r.url||""},
  {key:"festivals",    label:"Festivals",         icon:"festival",
   T:r=>r.name, S:r=>r.location||"", M:r=>r.application_window||"", B:r=>r.requirements_fees||"", C:r=>r.url||""},
  {key:"competitions", label:"Competitions",      icon:"emoji_events",
   T:r=>r.name, S:r=>r.deadlines||"", M:r=>r.prizes_categories||"", B:r=>r.entry_fees_requirements||"", C:r=>r.url||""},
  {key:"ad_agencies",  label:"Ad Agencies",       icon:"campaign",
   T:r=>r.name, S:r=>r.location||"", M:r=>r.website||"", B:r=>r.creative_director_or_leads||"", C:r=>r.contact_info||""},
  {key:"indie_games",  label:"Indie Video Games", icon:"sports_esports",
   T:r=>r.name||r.studio, S:r=>r.genre||"", M:r=>r.platform||"", B:r=>r.music_needs||"", C:r=>r.contact||""},
  {key:"restricted_resources",label:"Restricted", icon:"lock",
   T:r=>r.source_name, S:r=>r.url||"", M:r=>"", B:r=>r.reason_for_restriction||"", C:r=>r.expected_value||""},
];

// ══ STATE ══════════════════════════════════════════════════════════════
let activeCat  = CATS[0];
let activeData = [];
let view       = 'card';

// Physics — `angle` is fractional card index (0 = card 0 active, 1.5 = halfway between 1 and 2)
let angle      = 0;
let targetAngle= 0;
let velocity   = 0;
const FRICTION = 0.86;   // 0.86 = snappy, 0.95 = heavy/tactile
let isDragging = false, lastY = 0;

// Stack config
const DEPTH_PER_CARD = 55;   // px: each stacked card is this far behind the previous
const MAX_VISIBLE    = 6;    // cards rendered beyond front in each direction

const cardStage = document.getElementById('cardStage');
const ndots     = document.getElementById('ndots');
const counter   = document.getElementById('counter');
const showcase  = document.getElementById('showcase');
const spineEl   = document.getElementById('spine');

// ══ NAV ════════════════════════════════════════════════════════════════
function buildNav() {
  const nav = document.getElementById('nav');
  nav.innerHTML = '';
  CATS.forEach(cat => {
    const records = CAT[cat.key] || [];
    if (!records.length) return;
    const el = document.createElement('div');
    el.className = 'nav-item' + (cat.key === activeCat.key ? ' active' : '');
    el.id = 'ni-' + cat.key;
    el.onclick = () => switchCat(cat.key);
    el.innerHTML = `<span class="material-symbols-outlined text-[17px]">${cat.icon}</span><span>${cat.label}</span><span class="nc">${records.length}</span>`;
    nav.appendChild(el);
  });
}

function switchCat(key) {
  if (key === activeCat.key) return;
  activeCat  = CATS.find(c => c.key === key);
  activeData = CAT[key] || [];
  document.querySelectorAll('.nav-item').forEach(e => e.classList.remove('active'));
  const ni = document.getElementById('ni-' + key);
  if (ni) ni.classList.add('active');
  document.getElementById('htitle').textContent = activeCat.label;
  document.getElementById('gtitle').textContent = activeCat.label;
  document.getElementById('hcount').textContent = activeData.length + ' records';
  angle = 0; targetAngle = 0; velocity = 0;
  if (view === 'card') initCards();
  else renderGrid(activeData);
}

// ══ CARD BUILDER ═══════════════════════════════════════════════════════
function initCards() {
  cardStage.innerHTML = '';
  ndots.innerHTML     = '';
  const data = activeData;
  const cat  = activeCat;
  if (!data.length) {
    cardStage.innerHTML = '<div style="color:#859397;position:absolute;top:50%;left:50%;transform:translate(-50%,-50%)">No records.</div>';
    return;
  }

  data.forEach((rec, i) => {
    const cy  = i % 3;
    const cls = cy===0?'cd':cy===1?'cl':'ca';
    const ac  = cy===0?'#22d3ee':cy===1?'#aa0266':'#fff';
    const sbg = cy===0?'rgba(0,0,0,.14)':cy===1?'rgba(0,0,0,.07)':'rgba(0,0,0,.2)';
    const bbg = cy===0?'rgba(34,211,238,.11)':cy===1?'rgba(170,2,102,.11)':'rgba(255,255,255,.13)';

    const el = document.createElement('div');
    el.className = 'rolo-card ' + cls;
    el.dataset.idx = i;
    el.dataset.s   = 'hidden';

    const t = cat.T(rec)||'—', s = cat.S(rec)||'', m = cat.M(rec)||'';
    const b = cat.B(rec)||'',  c = cat.C(rec)||'';

    el.innerHTML = `
      <div class="flex flex-col h-full gap-3">
        <div class="flex justify-between items-start">
          <div class="w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0"
               style="background:${sbg};border:1px solid ${ac}22">
            <span class="material-symbols-outlined text-xl" style="color:${ac}">${cat.icon}</span>
          </div>
          <div class="text-right">
            <span class="text-[9px] font-black tracking-widest uppercase px-2 py-1 rounded-full"
                  style="background:${bbg};color:${ac}">Verified</span>
            <p class="text-[9px] opacity-45 mt-1 font-mono">SNK-${1000+i}</p>
          </div>
        </div>
        <div class="min-w-0">
          <h2 class="font-black text-[22px] leading-tight tracking-tight">${t}</h2>
          ${s?`<p class="text-sm opacity-60 mt-0.5 truncate">${s}</p>`:''}
          ${m?`<p class="text-[11px] opacity-45 mt-1 truncate">${m}</p>`:''}
        </div>
        ${b?`<div class="rounded-xl p-3 flex-1 overflow-hidden" style="background:${sbg}">
          <p class="text-[9px] font-black uppercase tracking-wider opacity-40 mb-1">Details</p>
          <p class="text-[12px] leading-relaxed opacity-80 line-clamp-4">${b}</p>
        </div>`:'<div class="flex-1"></div>'}
        <div class="flex gap-2 mt-auto flex-shrink-0">
          <button class="font-bold text-[12px] px-4 py-2.5 rounded-xl flex-1 flex items-center justify-center gap-1.5 shadow-md transition-all hover:scale-[1.02] active:scale-95"
                  style="background:${ac};color:${cy===1?'#fff':'#00363e'}">
            ${c&&c.startsWith('http')?'Visit Site':c&&c.includes('@')?'Email':'View Details'}
            <span class="material-symbols-outlined text-[13px]">open_in_new</span>
          </button>
          <button class="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
                  style="background:${sbg};border:1px solid ${ac}20">
            <span class="material-symbols-outlined text-[17px]" style="color:${ac}">bookmark</span>
          </button>
        </div>
      </div>`;
    cardStage.appendChild(el);

    const dot = document.createElement('div');
    dot.className = 'd';
    ndots.appendChild(dot);
  });

  positionSpine();
  render();
}

function positionSpine() {
  // Spine sits at bottom of card-stage in scene coordinates
  const stageRect = cardStage.getBoundingClientRect();
  const sceneRect = document.getElementById('scene').getBoundingClientRect();
  spineEl.style.top  = (stageRect.bottom - sceneRect.top + 4) + 'px';
  spineEl.style.left = '50%';
  spineEl.style.transform = 'translateX(-50%)';
  spineEl.style.position = 'absolute';
}

// ══ RENDER ═════════════════════════════════════════════════════════════
// The "looking down at a deck" effect:
//   - active card (rel≈0):  translateZ(0)  — at the surface, fully visible
//   - upcoming (rel>0):     translateZ(-rel * DEPTH) — further back = higher up + smaller
//   - past (rel<0):         translateZ(-|rel| * DEPTH) also, but fade out quickly
//
// perspective-origin above the scene center does all the visual magic:
// cards further in Z appear to recede toward the top of the screen

function render() {
  const n = cardStage.children.length;
  if (!n) return;

  const selIdx = ((Math.round(angle) % n) + n) % n;

  for (let i = 0; i < n; i++) {
    const el = cardStage.children[i];

    // Fractional relative index: 0 = active, +1 = one ahead, -1 = one past
    let rel = i - angle;
    // Shortest path wrap
    while (rel >  n/2) rel -= n;
    while (rel < -n/2) rel += n;

    const absRel = Math.abs(rel);

    // Beyond MAX_VISIBLE — hide
    if (absRel > MAX_VISIBLE) {
      el.dataset.s     = 'hidden';
      el.style.opacity = '0';
      el.style.zIndex  = '0';
      el.style.transform = `translateZ(-${MAX_VISIBLE * DEPTH_PER_CARD}px)`;
      continue;
    }

    const depth = absRel * DEPTH_PER_CARD;
    el.style.transform = `translateZ(-${depth.toFixed(2)}px)`;

    if (absRel < 0.4) {
      // Active card — sharp, full opacity, on top
      el.dataset.s     = 'active';
      el.style.opacity = '1';
      el.style.zIndex  = '200';
    } else if (rel > 0) {
      // Upcoming — visible stack receding behind
      el.dataset.s     = 'behind';
      el.style.opacity = Math.max(0, 1 - absRel * 0.25).toFixed(3);
      el.style.zIndex  = String(Math.round(200 - rel * 20));
    } else {
      // Past — fade out quickly as they go behind
      el.dataset.s     = 'gone';
      el.style.opacity = Math.max(0, 1 - absRel * 0.7).toFixed(3);
      el.style.zIndex  = '1';
    }
  }

  // Nav dots
  const dds = ndots.children;
  for (let i = 0; i < dds.length; i++) dds[i].className = (i===selIdx)?'d on':'d';
  counter.textContent = `${selIdx+1} / ${n}`;
}

// ══ PHYSICS ════════════════════════════════════════════════════════════
function snapToCard() {
  const n = cardStage.children.length || 1;
  targetAngle = Math.round(angle);
  // Keep in valid range
  targetAngle = ((targetAngle % n) + n) % n;
  // Prefer the direction with less travel
  let diff = targetAngle - angle;
  if (diff >  n/2) targetAngle -= n;
  if (diff < -n/2) targetAngle += n;
}

function physicsLoop() {
  if (!isDragging) {
    const diff = targetAngle - angle;
    angle    += diff * 0.14;
    angle    += velocity;
    velocity *= FRICTION;
    if (Math.abs(diff) < 0.004 && Math.abs(velocity) < 0.004) {
      angle    = targetAngle;
      velocity = 0;
    }
  }
  render();
  requestAnimationFrame(physicsLoop);
}

function step(dir) {
  const n = cardStage.children.length || 1;
  targetAngle = Math.round(angle) + dir;
}

// ══ INTERACTIONS ═══════════════════════════════════════════════════════
showcase.addEventListener('mousedown', e => {
  isDragging = true; lastY = e.clientY; velocity = 0;
  showcase.style.cursor = 'grabbing';
});
window.addEventListener('mousemove', e => {
  if (!isDragging) return;
  const dy  = e.clientY - lastY; lastY = e.clientY;
  // Dragging down = previous card (negative rel), up = next card
  const sens = 1 / 80;  // pixels per fractional card
  angle    -= dy * sens;
  velocity  = -dy * sens * 0.5;
});
window.addEventListener('mouseup', () => {
  if (!isDragging) return;
  isDragging = false; showcase.style.cursor = 'grab';
  snapToCard();
});

showcase.addEventListener('touchstart', e=>{isDragging=true;lastY=e.touches[0].clientY;velocity=0;},{passive:true});
window.addEventListener('touchmove', e=>{
  if (!isDragging) return;
  const dy=e.touches[0].clientY-lastY; lastY=e.touches[0].clientY;
  angle-=dy/80; velocity=-dy/80*0.5;
},{passive:true});
window.addEventListener('touchend',()=>{isDragging=false;snapToCard();});

showcase.addEventListener('wheel', e=>{
  e.preventDefault();
  targetAngle = Math.round(angle) + Math.sign(e.deltaY);
},{passive:false});

window.addEventListener('keydown', e=>{
  if (view!=='card') return;
  if (e.key==='ArrowDown'||e.key==='ArrowRight'){e.preventDefault();step(1);}
  if (e.key==='ArrowUp'  ||e.key==='ArrowLeft') {e.preventDefault();step(-1);}
});

// ══ VIEW TOGGLE ════════════════════════════════════════════════════════
function toggleView() {
  const tog=document.getElementById('vtog');
  const sc=document.getElementById('showcase');
  const gv=document.getElementById('gridview');
  if (view==='card') {
    view='grid'; tog.dataset.v='grid';
    sc.classList.add('hidden'); gv.classList.remove('hidden'); gv.style.display='flex'; gv.style.flexDirection='column';
    document.getElementById('vs').classList.remove('on'); document.getElementById('vg').classList.add('on');
    renderGrid(activeData);
  } else {
    view='card'; tog.dataset.v='card';
    gv.classList.add('hidden'); gv.style.display='';
    sc.classList.remove('hidden');
    document.getElementById('vs').classList.add('on'); document.getElementById('vg').classList.remove('on');
  }
}

// ══ GRID ═══════════════════════════════════════════════════════════════
let gridData=[];
function renderGrid(data){
  gridData=data; const cat=activeCat, g=document.getElementById('grid');
  g.innerHTML=''; document.getElementById('srch').value='';
  if (!data.length){g.innerHTML='<div class="col-span-3 text-center text-outline py-16">No records.</div>';return;}
  data.forEach((rec,i)=>{
    const ac=i%3===0?'#22d3ee':i%3===1?'#aa0266':'#ff7aba';
    const el=document.createElement('div'); el.className='bento';
    el.innerHTML=`<div class="flex items-start justify-between"><div><p class="text-[9px] font-black tracking-widest uppercase mb-1" style="color:${ac}">${cat.label}</p><h3 class="text-[14px] font-black leading-tight">${cat.T(rec)||'—'}</h3>${cat.S(rec)?`<p class="text-[11px] text-outline mt-0.5">${cat.S(rec)}</p>`:''}</div><span class="material-symbols-outlined text-[19px] opacity-25">${cat.icon}</span></div>${cat.B(rec)?`<p class="text-[11px] text-on-surface-variant leading-relaxed line-clamp-3">${cat.B(rec)}</p>`:''}${cat.C(rec)&&cat.C(rec).length<100?`<div class="text-[10px] font-mono text-outline/55 truncate">${cat.C(rec)}</div>`:''}`;
    g.appendChild(el);
  });
}
function filterGrid(q){
  const cat=activeCat,f=q.trim().toLowerCase();
  renderGrid(f?gridData.filter(r=>(cat.T(r)+cat.S(r)+cat.B(r)+cat.C(r)).toLowerCase().includes(f)):gridData);
}

// ══ AGENT MAP ══════════════════════════════════════════════════════════
let rafMap=null;
function drawMap(){
  const cv=document.getElementById('acanvas');
  const W=cv.offsetWidth||660,H=cv.offsetHeight||380;
  cv.width=W;cv.height=H;
  const cx=cv.getContext('2d');
  cx.fillStyle='#040810';cx.fillRect(0,0,W,H);
  cx.strokeStyle='rgba(60,73,76,.22)';cx.lineWidth=.5;
  for(let x=0;x<W;x+=36){cx.beginPath();cx.moveTo(x,0);cx.lineTo(x,H);cx.stroke()}
  for(let y=0;y<H;y+=36){cx.beginPath();cx.moveTo(0,y);cx.lineTo(W,y);cx.stroke()}
  const mx=W/2,my=H/2;
  const g=cx.createRadialGradient(mx,my,0,mx,my,48);
  g.addColorStop(0,'rgba(170,2,102,.75)');g.addColorStop(1,'rgba(170,2,102,0)');
  cx.beginPath();cx.arc(mx,my,48,0,Math.PI*2);cx.fillStyle=g;cx.fill();
  cx.beginPath();cx.arc(mx,my,20,0,Math.PI*2);cx.fillStyle='#aa0266';cx.fill();
  cx.strokeStyle='#ff7aba';cx.lineWidth=2;cx.stroke();
  cx.fillStyle='#fff';cx.font='bold 10px Inter';cx.textAlign='center';cx.textBaseline='middle';cx.fillText('MEDUSA',mx,my);
  const names=['Agencies','Supervisors','Platforms','Libraries','Grants','Festivals','Competitions','Ad Agencies','Games'];
  const cols=['#22d3ee','#00f2d0','#3b82f6','#8b5cf6','#22d3ee','#f59e0b','#10b981','#22d3ee','#ec4899'];
  const R=Math.min(W,H)*.34;
  names.forEach((nm,i)=>{
    const a=-Math.PI/2+(Math.PI*2/9)*i;
    const ax=mx+Math.cos(a)*R,ay=my+Math.sin(a)*R;
    cx.setLineDash([5,5]);cx.lineDashOffset=-performance.now()*.02;
    const lg=cx.createLinearGradient(mx,my,ax,ay);
    lg.addColorStop(0,cols[i]+'00');lg.addColorStop(.5,cols[i]+'77');lg.addColorStop(1,cols[i]+'cc');
    cx.strokeStyle=lg;cx.lineWidth=1.5;cx.beginPath();cx.moveTo(mx,my);cx.lineTo(ax,ay);cx.stroke();cx.setLineDash([]);
    const ng=cx.createRadialGradient(ax,ay,0,ax,ay,24);
    ng.addColorStop(0,cols[i]+'44');ng.addColorStop(1,cols[i]+'00');
    cx.beginPath();cx.arc(ax,ay,24,0,Math.PI*2);cx.fillStyle=ng;cx.fill();
    cx.beginPath();cx.arc(ax,ay,8,0,Math.PI*2);cx.fillStyle=cols[i];cx.fill();
    cx.strokeStyle='#0b1326';cx.lineWidth=2;cx.stroke();
    cx.fillStyle=cols[i];cx.font='bold 7px Inter';cx.textAlign='center';cx.textBaseline='middle';
    cx.fillText(nm.toUpperCase(),ax+Math.cos(a)*22,ay+Math.sin(a)*22);
  });
  rafMap=requestAnimationFrame(drawMap);
}
function openMap(){const m=document.getElementById('mapmodal');m.classList.remove('hidden');m.style.display='flex';drawMap();}
function closeMap(){document.getElementById('mapmodal').classList.add('hidden');document.getElementById('mapmodal').style.display='';cancelAnimationFrame(rafMap);}

// ══ BOOT ═══════════════════════════════════════════════════════════════
(function(){
  let tot=0;Object.values(CAT).forEach(v=>{if(Array.isArray(v))tot+=v.length});
  document.getElementById('mtotal').textContent=tot;
  buildNav();
  activeCat=CATS[0];
  activeData=CAT[activeCat.key]||[];
  document.getElementById('htitle').textContent=activeCat.label;
  document.getElementById('hcount').textContent=activeData.length+' records';
  initCards();
  requestAnimationFrame(physicsLoop);
  window.addEventListener('resize', positionSpine);
})();
</script>
</body>
</html>
"""

output = HTML.replace('CATALOGUE_JSON_PLACEHOLDER', json.dumps(cat))
out_path = os.path.join(base, 'dashboard.html')
with open(out_path, 'w') as f:
    f.write(output)

lines = output.count('\n')
print(f"dashboard.html written: {len(output):,} bytes, {lines} lines")
print(f"Catalogue: {sum(len(v) for v in cat.values() if isinstance(v,list))} records across {len(cat)} categories")
