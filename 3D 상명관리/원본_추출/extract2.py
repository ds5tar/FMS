# 평면도에서 벽·랙·기둥·에어컨을 뽑는다. 바닥 타일 21px = 600mm 가 기준자다.
from PIL import Image, ImageFilter
import numpy as np, json

SRC = "/sessions/jolly-gifted-tesla/mnt/uploads/cae team2017_DSR_C_A.jpg"
a = np.array(Image.open(SRC).convert("L")).astype(int)
H, W = a.shape
MM = 600.0 / 21.0          # 픽셀당 밀리미터

def 덩어리(mask, 최소):
    lab = np.zeros(mask.shape, np.int32); nxt = 1; par = {0:0}
    def find(x):
        while par[x]!=x: par[x]=par[par[x]]; x=par[x]
        return x
    for y in range(mask.shape[0]):
        for x in np.flatnonzero(mask[y]):
            상 = lab[y-1,x] if y else 0
            좌 = lab[y,x-1] if x else 0
            if 상 and 좌:
                lab[y,x]=min(상,좌)
                r1,r2 = find(상), find(좌)
                if r1!=r2: par[max(r1,r2)] = min(r1,r2)
            elif 상: lab[y,x]=상
            elif 좌: lab[y,x]=좌
            else: lab[y,x]=nxt; par[nxt]=nxt; nxt+=1
    for l in range(1, nxt): par[l] = find(l)
    flat = np.array([0]+[par[i] for i in range(1,nxt)])[lab]
    out=[]
    for l in np.unique(flat):
        if l==0: continue
        ys,xs = np.nonzero(flat==l)
        if len(ys) < 최소: continue
        out.append(dict(x0=int(xs.min()), y0=int(ys.min()),
                        x1=int(xs.max())+1, y1=int(ys.max())+1, area=int(len(ys))))
    return out

# ── ① 벽 (검정, 긴 선) ────────────────────────────────────────────────
검정 = a < 45
벽 = [r for r in 덩어리(검정, 800)
      if max(r["x1"]-r["x0"], r["y1"]-r["y0"]) > 80]

# ── ② 기둥 (검정 작은 정사각) ─────────────────────────────────────────
기둥 = [r for r in 덩어리(검정, 300)
        if 15 < r["x1"]-r["x0"] < 60 and 15 < r["y1"]-r["y0"] < 60
        and r["area"] > 0.7*(r["x1"]-r["x0"])*(r["y1"]-r["y0"])]

# ── ③ 랙 (중간 회색 해칭) ─────────────────────────────────────────────
m = np.array(Image.fromarray(((a>50)&(a<135)).astype(np.uint8)*255)
             .filter(ImageFilter.MaxFilter(5))) > 128
랙덩어리 = [r for r in 덩어리(m, 1200)
            if 15 < r["x1"]-r["x0"] < 70 and r["y1"]-r["y0"] > 55
            and 190 < r["y0"] < 320 or
            (15 < r["x1"]-r["x0"] < 70 and r["y1"]-r["y0"] > 150
             and 190 < r["y0"] < 460)]
# 같은 x 대역이면 하나로 합친다 (기둥이 가운데를 끊어 놓은 경우)
랙덩어리.sort(key=lambda r: (r["x0"], r["y0"]))
합침 = []
for r in 랙덩어리:
    앞 = 합침[-1] if 합침 else None
    if 앞 and abs(앞["x0"]-r["x0"]) < 12 and r["y0"] - 앞["y1"] < 90:
        앞["y1"] = max(앞["y1"], r["y1"]); 앞["x1"] = max(앞["x1"], r["x1"])
    else:
        합침.append(dict(r))
랙 = [r for r in 합침 if r["y1"]-r["y0"] > 150]

# 각 랙 열의 세로 칸수·가로 열수를 센다
for r in 랙:
    폭 = r["x1"]-r["x0"]
    r["열"] = 2 if 폭 > 30 else 1
    r["칸"] = int(round((r["y1"]-r["y0"]) / 21.0))

# ── ④ 에어컨 (밝고 매끈한 사각형; 바닥은 격자 무늬라 분산이 크다) ──────
밝음 = a >= 234
표준편차 = np.array(Image.fromarray(a.astype(np.uint8))
                    .filter(ImageFilter.RankFilter(5, 24))).astype(int) - \
           np.array(Image.fromarray(a.astype(np.uint8))
                    .filter(ImageFilter.RankFilter(5, 0))).astype(int)
매끈 = 표준편차 < 12
에어컨 = [r for r in 덩어리(밝음 & 매끈, 1500)
          if 40 < r["x1"]-r["x0"] < 180 and 20 < r["y1"]-r["y0"] < 90
          and r["area"] > 0.6*(r["x1"]-r["x0"])*(r["y1"]-r["y0"])]

print(f"벽 {len(벽)} · 기둥 {len(기둥)} · 랙 {len(랙)} · 에어컨 {len(에어컨)}")
print(f"\n방 전체 {W*MM/1000:.1f} m × {H*MM/1000:.1f} m  (1px = {MM:.2f} mm)")
print("\n랙 열")
for r in sorted(랙, key=lambda r:r["x0"]):
    print(f"  x{r['x0']:4d}-{r['x1']:4d} y{r['y0']:3d}-{r['y1']:3d}  "
          f"{r['열']}열 × {r['칸']}칸 = {r['열']*r['칸']:3d}대  "
          f"({(r['x1']-r['x0'])*MM/1000:.1f} × {(r['y1']-r['y0'])*MM/1000:.1f} m)")
print("\n에어컨")
for r in sorted(에어컨, key=lambda r:(r["y0"]//80, r["x0"])):
    print(f"  x{r['x0']:4d}-{r['x1']:4d} y{r['y0']:3d}-{r['y1']:3d}  "
          f"{(r['x1']-r['x0'])*MM/1000:.2f} × {(r['y1']-r['y0'])*MM/1000:.2f} m")
json.dump({"mm_per_px": MM, "W": W, "H": H, "벽": 벽, "기둥": 기둥,
           "랙": 랙, "에어컨": 에어컨},
          open("geom.json","w"), ensure_ascii=False, indent=1)
