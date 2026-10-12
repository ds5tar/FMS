# 평면도 좌표를 3차원 장면(미터 단위)으로 바꾼다
from PIL import Image, ImageFilter
import numpy as np, json

a = np.array(Image.open("/sessions/jolly-gifted-tesla/mnt/uploads/"
                        "cae team2017_DSR_C_A.jpg").convert("L")).astype(int)
H, W = a.shape
G = json.load(open("geom.json"))
M = G["mm_per_px"] / 1000.0          # 픽셀 → 미터
TILE = 21                            # 바닥 타일 21px = 600mm

# 통상 치수 (사용자가 실측을 모른다고 해서 표준값을 쓴다)
높이 = {"랙": 2.0,        # 42U
        "에어컨": 2.0,     # 항온항습기 본체
        "기둥": 3.6,      # 슬래브까지
        "벽": 3.6}
랙깊이 = 0.6                          # 도면이 타일 한 칸(600)으로 그렸다
랙폭 = 0.6

def m(px): return round(px * M, 3)

장면 = {"단위": "m", "타일mm": 600, "px당mm": round(G["mm_per_px"], 3),
        "방": {"w": m(W), "d": m(H)},
        "랙": [], "에어컨": [], "기둥": [], "벽": [], "바닥": []}

# ── 랙: 해칭 칸 하나가 랙 한 대다 ─────────────────────────────────────
번호 = 0
for r in sorted(G["랙"], key=lambda r: r["x0"]):
    열 = r["열"]; 칸 = r["칸"]
    폭px = (r["x1"] - r["x0"]) / 열
    for c in range(열):
        for i in range(칸):
            번호 += 1
            x = r["x0"] + c * 폭px
            y = r["y0"] + i * (r["y1"] - r["y0"]) / 칸
            장면["랙"].append({
                "id": f"R{번호:03d}",
                "x": m(x), "y": m(y), "w": 랙폭, "d": 랙깊이,
                "h": 높이["랙"],
                "열": f"{'ABCDEFGHI'[sorted(G['랙'], key=lambda q:q['x0']).index(r)]}"
                      f"{c+1}"})

# ── 에어컨 ───────────────────────────────────────────────────────────
for i, r in enumerate(sorted(G["에어컨"], key=lambda r: (r["y0"]//80, r["x0"])), 1):
    장면["에어컨"].append({
        "id": f"AC{i:02d}", "x": m(r["x0"]), "y": m(r["y0"]),
        "w": m(r["x1"]-r["x0"]), "d": m(r["y1"]-r["y0"]), "h": 높이["에어컨"]})

# ── 기둥 ─────────────────────────────────────────────────────────────
for i, r in enumerate(sorted(G["기둥"], key=lambda r: (r["y0"]//100, r["x0"])), 1):
    장면["기둥"].append({
        "id": f"C{i:02d}", "x": m(r["x0"]), "y": m(r["y0"]),
        "w": m(r["x1"]-r["x0"]), "d": m(r["y1"]-r["y0"]), "h": 높이["기둥"]})

# ── 바닥: 방의 실내 영역 ─────────────────────────────────────────────
#
# **「밝은 화소」 로 잡으면 안 된다.** 랙·기둥은 어두워서 바닥에서 빠지고,
# 그러면 아래 벽 만들기가 그 구멍마다 벽을 세운다 — 실내 한가운데
# 랙마다 벽이 둘러쳐졌다. 실제로 그렇게 나왔다.
#
# 실내는 「바깥에서 물을 부어 안 닿는 곳」 이다. 바깥 테두리에서 벽을
# 넘지 못하게 채우면 남는 것이 실내다. 랙이 어둡든 말든 상관이 없다.
from PIL import ImageDraw
벽화소 = a < 45
칠 = Image.fromarray(np.where(벽화소, 0, 255).astype(np.uint8))
ImageDraw.floodfill(칠, (0, 0), 128)
바깥 = np.array(칠) == 128
실내 = (~바깥) & (~벽화소)

셀y, 셀x = H // TILE + 1, W // TILE + 1
바닥격자 = np.zeros((셀y, 셀x), bool)
for gy in range(셀y):
    for gx in range(셀x):
        블록 = 실내[gy*TILE:(gy+1)*TILE, gx*TILE:(gx+1)*TILE]
        # **문턱을 높게 잡는다(0.85).** 0.5 로 두면 칸막이벽이 사라진다 —
        # 벽 두께가 8px 이고 타일이 21px 이라, 벽이 지나가는 칸도 실내
        # 비율이 0.6 이 넘어 바닥으로 잡힌다. 그러면 벽을 세울 경계가
        # 없어져서 방 안의 칸막이가 통째로 없어진다.
        if 블록.size and 블록.mean() > 0.85:
            바닥격자[gy, gx] = True

def 큰사각형(격자):
    """참인 칸을 최대 사각형들로 덮는다 (탐욕적). 조각 수가 크게 준다."""
    남 = 격자.copy(); out = []
    while 남.any():
        ys, xs = np.nonzero(남)
        gy = int(ys[0]); gx = int(xs[np.flatnonzero(ys == ys[0])[0]])
        w = 0
        while gx + w < 남.shape[1] and 남[gy, gx+w]: w += 1
        h = 1
        while gy + h < 남.shape[0] and 남[gy+h, gx:gx+w].all(): h += 1
        남[gy:gy+h, gx:gx+w] = False
        out.append((gx, gy, w, h))
    return out

for gx, gy, w, h in 큰사각형(바닥격자):
    장면["바닥"].append({"x": m(gx*TILE), "y": m(gy*TILE),
                        "w": m(w*TILE), "d": m(h*TILE)})

# ── 벽: 바닥 영역의 경계를 따라 세운다 ───────────────────────────────
#
# **검정 화소를 격자로 내리는 방법은 안 됐다.** 외벽 선이 8px 인데 타일이
# 21px 이라 한 칸의 검정 비율이 0.38 언저리에서 오르내린다. 문턱값 하나로는
# 어떤 줄은 남고 어떤 줄은 빠져서 **벽이 군데군데 뚫렸다.**
#
# 바닥 경계를 쓰면 그 흔들림이 없다. 바닥 칸의 이웃이 바닥이 아니면 그
# 변에 벽을 세운다 — 오른쪽이 두 번 꺾인 모양도 그대로 따라온다.
두께 = 0.3
T = TILE * M
조각 = []
for gy in range(셀y):
    for gx in range(셀x):
        if not 바닥격자[gy, gx]: continue
        X, Y = gx*T, gy*T
        if gy == 0        or not 바닥격자[gy-1, gx]: 조각.append((X, Y-두께, T, 두께))
        if gy == 셀y-1    or not 바닥격자[gy+1, gx]: 조각.append((X, Y+T, T, 두께))
        if gx == 0        or not 바닥격자[gy, gx-1]: 조각.append((X-두께, Y, 두께, T))
        if gx == 셀x-1    or not 바닥격자[gy, gx+1]: 조각.append((X+T, Y, 두께, T))

최대길이 = 3.0     # m

def 합치기(목록, 축):
    """이어지는 벽을 하나로. 다만 **너무 길게는 안 합친다.**

    3D 는 상자를 중심 깊이 순으로 뒤에서부터 그린다(화가 알고리즘).
    46m 짜리 벽 하나는 중심 깊이가 그 벽 어느 쪽도 대표하지 못해서,
    한쪽 끝에서는 랙 앞으로 잘못 그려진다 — 실제로 그렇게 나왔다.
    짧게 끊으면 중심 깊이가 제 구실을 한다.
    """
    키 = (lambda r: (round(r[1],3), round(r[0],3))) if 축 == "x" else \
         (lambda r: (round(r[0],3), round(r[1],3)))
    목록 = sorted(목록, key=키); out = []
    for x, y, w, d in 목록:
        if out:
            px, py, pw, pd = out[-1]
            if 축 == "x" and abs(py-y) < 1e-6 and abs(pd-d) < 1e-6 \
               and abs(px+pw-x) < 1e-6 and pw + w <= 최대길이:
                out[-1] = (px, py, pw+w, pd); continue
            if 축 == "y" and abs(px-x) < 1e-6 and abs(pw-w) < 1e-6 \
               and abs(py+pd-y) < 1e-6 and pd + d <= 최대길이:
                out[-1] = (px, py, pw, pd+d); continue
        out.append((x, y, w, d))
    return out

for x, y, w, d in (합치기([r for r in 조각 if r[2] > r[3]], "x") +
                   합치기([r for r in 조각 if r[2] <= r[3]], "y")):
    장면["벽"].append({"x": round(x,3), "y": round(y,3), "w": round(w,3),
                      "d": round(d,3), "h": 높이["벽"]})

json.dump(장면, open("scene.json","w"), ensure_ascii=False)
print(f"방 {장면['방']['w']} × {장면['방']['d']} m")
print(f"랙 {len(장면['랙'])}대 · 에어컨 {len(장면['에어컨'])}대 · "
      f"기둥 {len(장면['기둥'])}개 · 벽 {len(장면['벽'])}조각 · "
      f"바닥 {len(장면['바닥'])}조각")
