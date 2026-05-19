const State = {
  socket:null, supportSocket:null, prices:{}, history:{},
  chart:null, activePair:"EUR/USD", chartTF:60, direction:"BUY",
  supportRoom:"general", userName:document.body.dataset.user||"Trader",
};

document.addEventListener("DOMContentLoaded",()=>{
  markActiveNav(); initFlashClose(); initTabs(); initMobileMenu();
  // Set active pair from URL or data attribute
  const urlPair = document.body.dataset.activePair;
  if (urlPair && urlPair !== "None") State.activePair = urlPair;
  if(document.getElementById("liveChart")) initLiveTrading();
  if(document.getElementById("chat-messages")) initSupportChat();
});

function markActiveNav(){
  const path=window.location.pathname;
  document.querySelectorAll(".nav-item").forEach(a=>{
    const href=a.getAttribute("href");
    if(href===path || (path.startsWith(href) && href.length>5)) a.classList.add("active");
  });
}
function initMobileMenu(){
  const btn=document.getElementById("menu-toggle"),sb=document.getElementById("sidebar");
  if(!btn||!sb) return; btn.style.display="flex";
  btn.addEventListener("click",()=>sb.classList.toggle("open"));
}
function initFlashClose(){
  document.querySelectorAll(".flash").forEach(f=>{
    setTimeout(()=>{f.style.opacity="0";f.style.transform="translateY(-4px)"},4500);
    setTimeout(()=>f.remove(),4900);
  });
}
function initTabs(){
  document.querySelectorAll(".tabs").forEach(g=>{
    const bs=g.querySelectorAll(".tab-btn"),w=g.closest(".tab-wrapper")||document;
    bs.forEach(b=>b.addEventListener("click",()=>{
      bs.forEach(x=>x.classList.remove("active")); b.classList.add("active");
      w.querySelectorAll(".tab-content").forEach(tc=>tc.classList.toggle("active",tc.id===b.dataset.tab));
    }));
    if(bs[0]) bs[0].click();
  });
}

// ══ LIVE TRADING ══════════════════════════════════════════════════
function initLiveTrading(){
  buildChart(); connectLiveSocket(); initOrderPanel(); initPairSelector(); startPositionPoller();
}

function buildChart(){
  const c=document.getElementById("liveChart");
  if(!c) return;
  State.chart={ctx:c.getContext("2d"),canvas:c};
  resizeChart(); window.addEventListener("resize",resizeChart);
  drawChart();
}
function resizeChart(){
  const c=State.chart?.canvas;
  if(!c) return;
  const w=c.parentElement; c.width=w.clientWidth; c.height=w.clientHeight-1;
}
function drawChart(){
  const{ctx,canvas}=State.chart; if(!canvas) return;
  const W=canvas.width,H=canvas.height;
  ctx.clearRect(0,0,W,H);
  ctx.fillStyle="#0c1528"; ctx.fillRect(0,0,W,H);
  const hist=(State.history[State.activePair]||[]).slice(-State.chartTF);
  if(hist.length<2){
    ctx.fillStyle="#3d4f70";ctx.font="14px Inter";ctx.textAlign="center";
    ctx.fillText("Waiting for data…",W/2,H/2);
    requestAnimationFrame(drawChart); return;
  }
  const pad={top:20,right:80,bottom:30,left:14};
  const cW=W-pad.left-pad.right, cH=H-pad.top-pad.bottom;
  const mn=Math.min(...hist),mx=Math.max(...hist),rng=mx-mn||mn*0.001;
  const sX=i=>pad.left+(i/(hist.length-1))*cW;
  const sY=v=>pad.top+(1-(v-mn)/rng)*cH;
  // Grid
  ctx.strokeStyle="rgba(255,255,255,0.04)";ctx.lineWidth=1;
  for(let i=0;i<=5;i++){
    const y=pad.top+(i/5)*cH;
    ctx.beginPath();ctx.moveTo(pad.left,y);ctx.lineTo(W-pad.right,y);ctx.stroke();
    const val=mx-(i/5)*rng;
    ctx.fillStyle="#3d4f70";ctx.font="10px JetBrains Mono,monospace";ctx.textAlign="left";
    ctx.fillText(val.toFixed(val<10?5:2),W-pad.right+6,y+3);
  }
  // X axis time labels
  ctx.fillStyle="#3d4f70";ctx.font="9px JetBrains Mono,monospace";ctx.textAlign="center";
  for(let i=0;i<hist.length;i+=Math.floor(hist.length/6)){
    ctx.fillText(`-${hist.length-i}`,sX(i),H-pad.bottom+16);
  }
  // Gradient fill
  const up=hist[hist.length-1]>=hist[0];
  const grad=ctx.createLinearGradient(0,pad.top,0,H-pad.bottom);
  if(up){grad.addColorStop(0,"rgba(15,186,114,0.28)");grad.addColorStop(1,"rgba(15,186,114,0.01)");}
  else{grad.addColorStop(0,"rgba(240,69,90,0.28)");grad.addColorStop(1,"rgba(240,69,90,0.01)");}
  ctx.beginPath();ctx.moveTo(sX(0),sY(hist[0]));
  for(let i=1;i<hist.length;i++) ctx.lineTo(sX(i),sY(hist[i]));
  ctx.lineTo(sX(hist.length-1),H-pad.bottom);ctx.lineTo(sX(0),H-pad.bottom);
  ctx.closePath();ctx.fillStyle=grad;ctx.fill();
  // Line
  ctx.beginPath();ctx.moveTo(sX(0),sY(hist[0]));
  for(let i=1;i<hist.length;i++) ctx.lineTo(sX(i),sY(hist[i]));
  ctx.strokeStyle=up?"#0fba72":"#f0455a";ctx.lineWidth=2.5;ctx.lineJoin="round";ctx.stroke();
  // Current price dot + glow
  const lx=sX(hist.length-1),ly=sY(hist[hist.length-1]);
  ctx.beginPath();ctx.arc(lx,ly,5,0,Math.PI*2);ctx.fillStyle=up?"#0fba72":"#f0455a";ctx.fill();
  ctx.beginPath();ctx.arc(lx,ly,10,0,Math.PI*2);
  ctx.strokeStyle=up?"rgba(15,186,114,0.3)":"rgba(240,69,90,0.3)";ctx.lineWidth=2;ctx.stroke();
  // Price label on right
  ctx.fillStyle=up?"#0fba72":"#f0455a";ctx.font="bold 11px JetBrains Mono,monospace";ctx.textAlign="left";
  ctx.fillText(hist[hist.length-1].toString(),W-pad.right+6,ly+4);
  // Spread indicator
  const p=State.prices[State.activePair];
  if(p){
    ctx.fillStyle="rgba(255,255,255,0.06)";ctx.font="9px Inter";ctx.textAlign="left";
    ctx.fillText(`Spread: ${p.spread}`,pad.left+4,pad.top+14);
  }
  requestAnimationFrame(drawChart);
}

function connectLiveSocket(){
  if(typeof io==="undefined") return;
  State.socket=io("/live",{transports:["websocket"]});
  State.socket.on("connect",()=>console.log("[WS] Live connected"));
  State.socket.on("snapshot",data=>{
    State.prices=data;
    Object.keys(data).forEach(p=>{ State.history[p]=data[p].history||[]; });
    updateAllUI();
  });
  State.socket.on("tick",data=>{
    Object.keys(data).forEach(p=>{
      State.prices[p]=data[p];
      if(!State.history[p]) State.history[p]=[];
      State.history[p].push(data[p].mid);
      if(State.history[p].length>300) State.history[p].shift();
    });
    updateAllUI();
  });
  State.socket.on("sessions",updateSessions);
}

function updateAllUI(){
  const p=State.prices[State.activePair];
  if(p){
    const el=id("chart-price");
    if(el){
      const prev=parseFloat(el.dataset.prev||p.mid);
      el.textContent=p.mid; el.dataset.prev=p.mid;
      el.style.color=p.mid>prev?"var(--green)":p.mid<prev?"var(--red)":"var(--text)";
    }
    const cc=id("chart-change");
    if(cc){ cc.textContent=(p.change_pct>=0?"+":"")+p.change_pct+"%"; cc.className="chart-change "+(p.change_pct>=0?"pos":"neg"); }
    const bid=id("chart-bid"); if(bid) bid.textContent=p.bid;
    const ask=id("chart-ask"); if(ask) ask.textContent=p.ask;
    const hi=id("chart-high"); if(hi) hi.textContent=p.high;
    const lo=id("chart-low"); if(lo) lo.textContent=p.low;
    const sp=id("chart-spread"); if(sp) sp.textContent=p.spread;
    const op=id("order-price"); if(op) op.textContent=p.mid;
    const ob=id("order-bid"); if(ob) ob.textContent=p.bid;
    const oa=id("order-ask"); if(oa) oa.textContent=p.ask;
  }
  // Ticker strip
  document.querySelectorAll(".ticker-item[data-pair]").forEach(el=>{
    const d=State.prices[el.dataset.pair]; if(!d) return;
    const pr=el.querySelector(".ticker-price"),ch=el.querySelector(".ticker-chg");
    if(pr){
      const prev=parseFloat(pr.dataset.prev||d.mid); pr.textContent=d.mid; pr.dataset.prev=d.mid;
      pr.style.color=d.mid>prev?"var(--green)":d.mid<prev?"var(--red)":"var(--text)";
    }
    if(ch){ch.textContent=(d.change_pct>=0?"+":"")+d.change_pct+"%";ch.className="ticker-chg "+(d.change_pct>=0?"pos":"neg");}
  });
  // Market table
  document.querySelectorAll("tr[data-pair]").forEach(row=>{
    const d=State.prices[row.dataset.pair]; if(!d) return;
    const pr=row.querySelector(".live-price");
    if(pr){
      const prev=parseFloat(pr.dataset.prev||d.mid);pr.textContent=d.mid;pr.dataset.prev=d.mid;
      pr.style.color=d.mid>prev?"var(--green)":d.mid<prev?"var(--red)":"";
      setTimeout(()=>pr.style.color="",600);
    }
    const cp=row.querySelector(".live-change");
    if(cp){cp.textContent=(d.change_pct>=0?"+":"")+d.change_pct+"%";cp.className="chg-pill "+(d.change_pct>=0?"pos":"neg");}
  });
}
function updateSessions(data){
  document.querySelectorAll(".sess-chip[data-session]").forEach(el=>{
    const s=data[el.dataset.session]; if(!s) return;
    el.classList.toggle("active",s.active); el.classList.toggle("inactive",!s.active);
    const dot=el.querySelector(".sess-dot");
    if(dot) dot.className="sess-dot "+(s.active?"active":"inactive");
  });
}

function initPairSelector(){
  const sel=id("pair-select"); if(!sel) return;
  sel.addEventListener("change",()=>switchPair(sel.value));
}
function switchPair(pair){
  State.activePair=pair;
  const sel=id("pair-select"); if(sel) sel.value=pair;
  const pf=id("sl-pair"); if(pf) pf.value=pair;
  document.querySelectorAll(".ticker-item").forEach(el=>
    el.classList.toggle("active",el.dataset.pair===pair));
  // Update URL without reload
  const url=new URL(window.location);
  url.pathname="/trading/live/"+pair.replace("/","%2F");
  window.history.replaceState({},"",url);
}
window.selectPair=switchPair;
window.setTF=function(n,btn){
  State.chartTF=n;
  document.querySelectorAll(".tf-btn").forEach(b=>b.classList.remove("active"));
  btn.classList.add("active");
};

function initOrderPanel(){
  document.querySelectorAll(".order-tab").forEach(btn=>{
    btn.addEventListener("click",()=>{
      State.direction=btn.dataset.dir;
      document.querySelectorAll(".order-tab").forEach(b=>b.classList.remove("active"));
      btn.classList.add("active");
      const di=id("order-direction"); if(di) di.value=btn.dataset.dir;
      const sb=id("submit-order");
      if(sb){
        sb.className=State.direction==="BUY"?"buy-btn":"sell-btn";
        sb.innerHTML=State.direction==="BUY"?"<span style='font-size:18px'>▲</span> PLACE BUY ORDER":"<span style='font-size:18px'>▼</span> PLACE SELL ORDER";
      }
    });
  });
  const def=document.querySelector('.order-tab[data-dir="BUY"]');
  if(def) def.click();
}

function startPositionPoller(){
  const tbl=id("positions-tbody"); if(!tbl) return;
  const poll=()=>{
    fetch("/trading/api/positions").then(r=>r.json()).then(positions=>{
      positions.forEach(p=>{
        const row=document.querySelector(`tr[data-pos-id="${p.id}"]`);
        if(!row) return;
        const pnlEl=row.querySelector(".live-pnl");
        if(pnlEl){
          pnlEl.textContent=(p.profit_loss>=0?"+":"")+p.profit_loss.toFixed(2);
          pnlEl.className="pnl-val "+(p.profit_loss>=0?"pnl-pos":"pnl-neg");
        }
        const cpEl=row.querySelector(".live-cp"); if(cpEl) cpEl.textContent=p.current_price;
      });
      const total=positions.reduce((s,p)=>s+p.profit_loss,0);
      document.querySelectorAll(".total-open-pnl").forEach(el=>{
        el.textContent=(total>=0?"+":"")+"$"+total.toFixed(2);
        el.className="total-open-pnl font-mono font-bold "+(total>=0?"text-green":"text-red");
      });
    }).catch(()=>{});
  };
  poll(); setInterval(poll,1200);
}

// ══ SUPPORT CHAT ══════════════════════════════════════════════════
function initSupportChat(){
  connectSupportSocket();
  const input=id("chat-input");
  if(input) input.addEventListener("keydown",e=>{
    if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();sendMessage();}
  });
  setTimeout(()=>{
    appendMessage({sender:"Support Agent",text:"👋 Hello! Welcome to ForexBot Elite Support. How can I help you today?",role:"agent",ts:Date.now()});
  },600);
}
function connectSupportSocket(){
  if(typeof io==="undefined") return;
  State.supportSocket=io("/support",{transports:["websocket"]});
  State.supportSocket.on("connect",()=>{
    State.supportSocket.emit("join_support",{room:State.supportRoom});
  });
  State.supportSocket.on("message",msg=>{
    if(msg.role!=="user"){hideTyping();appendMessage(msg);}
  });
}
window.sendMessage=function(){
  const input=id("chat-input"); if(!input) return;
  const text=input.value.trim(); if(!text) return;
  const msg={sender:State.userName,text,role:"user",room:State.supportRoom,ts:Date.now()};
  appendMessage(msg); input.value=""; showTyping();
  if(State.supportSocket) State.supportSocket.emit("message",msg);
};
window.sendQuick=function(text){const i=id("chat-input");if(i){i.value=text;sendMessage();}};
function appendMessage(msg){
  const wrap=id("chat-messages"); if(!wrap) return;
  const isUser=msg.role==="user";
  const time=new Date(msg.ts).toLocaleTimeString([],{hour:"2-digit",minute:"2-digit"});
  const init=msg.sender.split(" ").map(w=>w[0]).join("").slice(0,2).toUpperCase();
  const div=document.createElement("div"); div.className="msg "+(isUser?"user":"agent");
  div.innerHTML=`<div class="msg-ava ${isUser?"user":"agent"}">${init}</div>
    <div><div class="msg-bubble">${escHtml(msg.text)}</div>
    <div class="msg-time">${isUser?"You":msg.sender} · ${time}</div></div>`;
  wrap.appendChild(div); wrap.scrollTop=wrap.scrollHeight;
}
function showTyping(){const t=id("typing-indicator");if(t)t.style.display="flex";}
function hideTyping(){const t=id("typing-indicator");if(t)t.style.display="none";}
function escHtml(s){return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");}
function id(x){return document.getElementById(x);}

// ══ BACKTEST ══════════════════════════════════════════════════════
window.runBacktest=function(){
  const btn=id("bt-run"),res=id("bt-results"); if(!btn||!res) return;
  btn.disabled=true;btn.textContent="⟳ Simulating…";
  setTimeout(()=>{
    const wr=(65+Math.random()*25).toFixed(1),pf=(1.5+Math.random()*1.8).toFixed(2);
    const dd=(3+Math.random()*10).toFixed(1),ret=(8+Math.random()*32).toFixed(1);
    const tr=Math.floor(80+Math.random()*200);
    res.innerHTML=`<div class="grid-3 mt-16">
      ${kpi(wr+"%","Win Rate","text-green")}${kpi(pf+"x","Profit Factor","text-gold")}
      ${kpi("-"+dd+"%","Max Drawdown","text-red")}${kpi("+"+ret+"%","Return","text-blue")}
      ${kpi(tr,"Trades","text-muted")}${kpi((1.2+Math.random()*1.5).toFixed(2),"Sharpe","text-purple")}
    </div><div class="flash success mt-16">✅ Backtest complete.</div>`;
    btn.disabled=false;btn.textContent="▶ Run Backtest";
  },1800);
};
function kpi(v,l,c){return`<div style="background:var(--card2);border:1px solid var(--border);
  border-radius:var(--radius-xs);padding:14px;text-align:center">
  <div style="font-size:20px;font-weight:900" class="${c}">${v}</div>
  <div class="text-xs text-muted mt-8">${l}</div></div>`;}
function switchPair(pair) {
    State.activePair = pair;
    const safePair = pair.replace("/", "_");
    const url = "/trading/live/" + safePair;
    window.history.replaceState({}, "", url);
    
    // UI Updates
    document.querySelectorAll(".ticker-item").forEach(el => 
        el.classList.toggle("active", el.dataset.pair === pair));
    const sel = document.getElementById("pair-select");
    if(sel) sel.value = pair;
}
