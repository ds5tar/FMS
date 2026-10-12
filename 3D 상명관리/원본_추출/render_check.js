// room3d.html 의 스크립트를 그대로 돌려 무엇을 그리는지 받아 적는다.
// 캔버스가 없는 환경이라 채운 다각형만 모아 파이썬이 그림으로 굽는다.
const fs = require("fs");
const html = fs.readFileSync(process.argv[2], "utf8");
const js = /<script>\n([\s\S]*?)\n<\/script>/.exec(html)[1];

const 그린것 = [];
let 현재 = null, 조각 = [], 채움 = "#000";
const ctx = {
  set fillStyle(v){ 채움 = v; }, get fillStyle(){ return 채움; },
  strokeStyle:"", lineWidth:1, lineJoin:"",
  setTransform(){}, fillRect(){},
  // moveTo 누적 — 한 경로에 여러 조각(그림자·격자선)이 들어올 수 있다
  beginPath(){ 조각 = []; 현재 = null; },
  moveTo(x,y){ 현재 = [[x,y]]; 조각.push(현재); },
  lineTo(x,y){ if (현재) 현재.push([x,y]); },
  closePath(){},
  fill(){ for (const c of 조각) if (c.length > 2)
            그린것.push({p:c.slice(), c:채움, 채움만:1}); },
  // **선도 받아 적는다.** 전에는 무시하고 파이썬이 전부 테두리를 그렸는데,
  // 그래서 화면에 없는 줄무늬가 그림에만 생겼다 — 검사기가 거짓말을 했다.
  stroke(){ for (const c of 조각)
              그린것.push({p:c.slice(), s:this.strokeStyle,
                          lw:this.lineWidth}); },
};
// 단추마다 다른 요소를 준다 — 하나를 돌려주면 마지막 onclick 만 남는다
const 요소 = {};
const el = (id) => (요소[id] = 요소[id] || {
  id, textContent:"", innerHTML:"", style:{}, onclick:null, checked:false,
  _on:{}, addEventListener(t,f){ this._on[t]=f; }, getContext:()=>ctx,
  width:0, height:0, setPointerCapture(){},
  classList:{add(){},remove(){}} });
const canvas = el("cv");
global.document = { getElementById:(id)=>el(id), createElement:()=>el("tmp") };
global.window = { devicePixelRatio:1 };
global.innerWidth = +(process.env.W||1600); global.innerHeight = +(process.env.H||900);
global.addEventListener = () => {};

new Function(js)();
// 시점 단추를 눌러 본다 (인자로 v_top, v_eye 등)
const 시점 = process.argv[3];
if (시점) { 그린것.length = 0; 요소[시점].onclick(); }
console.log(JSON.stringify({w:canvas.width, h:canvas.height, poly:그린것}));
