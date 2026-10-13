# 서울센터 3층 전산실의 3D 기본 배치(static/room3d_site_SEOUL.json)를 대시보드 「3층 전산실 배치도」(plan_3f.jpg)와 서울센터 센서로 만든다 — 71차
#
# 왜 (2026-10-13, 71차 사용자 「서울센터의 센서를 이용하여 3d 상명관리를 했을때 미리보기를 보여주고 실행」)
#   plan_3f.jpg 는 비스듬히 본 렌더 그림이라 치수가 없다. 그림의 배치를 미터로 옮긴 근사 배치다.
#     · 가로 1 px = 0.03 m, 세로 1 px = 0.026 m (랙 한 열 10대 = 6 m 가 그림의 열 길이와 맞게)
#     · 왼쪽 관제실, 위쪽 벽을 따라 항온항습기 9대(CRAC-01~09), 랙 14열(「1열」~「14열」, 열마다 10대),
#       오른쪽 복도와 전기실(UPS01·배터리)
#   센서는 배치도 마커(PLAN.*)의 자리를 그대로 옮기고, 장치가 분명한 것은 장비에 코드를 붙인다.
#     · PLAN.TEMP.01~14 → 온도 센서 (랙 속에 떨어지면 가까운 통로로 옮긴다)
#     · PLAN.LEAK.01~14 「N열 누수」 → 그 열을 따라 깐 누수 감지선, PLAN.LEAK.15·16 → 점형 누수 감지기
#     · PLAN.WIND.01~09 → 풍속 센서 (통로 안으로)
#     · RACK.RrCc.TEMP(랙 흡입온도 24개) → r열의 3~8번째 랙에 그 랙의 코드로
#     · CRAC-01~09 → 항온항습기 (코드 앞부분 — 환기온도·습도·펌프가 모두 붙는다), UPS01 → UPS, FIRE.01~04 → 연기 감지기,
#       ENV3F → 3층 실내 온습도
#   나머지(LEAK.01~21·WIND.01~09 등 자리 정보가 없는 센서)는 놓지 않는다 — 편집기 「FMS 센서」 판에서 끌어다 놓는다.
#
#   python3 room3d_seoul.py           # static/room3d_site_SEOUL.json 을 다시 만든다
#   python3 room3d_seoul.py --check   # 지금 파일이 최신인지

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "static" / "room3d_site_SEOUL.json"
INDEX = HERE / "static" / "room3d_sites.json"      # 현장 코드 → 기본 배치 파일 (3D 화면이 먼저 본다)
KX, KY = 0.03, 0.026            # m/px — plan_3f.jpg 1774×493
IW, IH = 1774, 493
W, D, H = 52.0, 12.6, 3.6

# 배치도 마커 자리 (%, 대시보드 FLOOR3 의 PLAN 위젯 — 50_api/demo_dashboards.py)
TEMP = [(13.2, 12.34), (26.78, 15.78), (45.35, 15.78), (53.8, 15.78), (67.95, 15.78), (89.58, 38.53),
        (26.78, 45.28), (34.28, 45.28), (45.35, 45.28), (53.8, 45.28), (62.72, 45.28), (71.42, 45.28),
        (79.31, 45.28), (92.33, 66.43)]
ROW_X = [22.48, 26.35, 30.32, 34.47, 38.57, 43.48, 48.75, 52.58, 56.14, 60.97, 64.75, 68.58, 72.64, 78.14]
LEAK_PT = [(83.66, 39.98), (83.66, 52.47)]
WIND = [22.45, 29.12, 37.51, 43.36, 49.85, 58.64, 67.21, 75.9, 85.95]
WIND_Y = 63.95
CRAC_PX = [435, 545, 655, 730, 870, 985, 1135, 1275, 1415]
COL_PX = [345, 580, 830, 1075, 1315, 1610]

ROW_Y0, RACKS = 3.4, 10          # 열 머리 y (m), 열마다 랙 수
HALL = (10.8, 45.2)               # 전산실 왼쪽·오른쪽 벽 x (m)


def mx(pct: float) -> float:
    return round(pct / 100 * IW * KX, 3)


def my(pct: float) -> float:
    return round(pct / 100 * IH * KY, 3)


def build() -> dict:
    items: list[dict] = []

    def add(kind, iid, x, y, w, d, h, z0=0.0, **more):
        items.append({"id": iid, "종류": kind, "이름": more.pop("이름", None) or NAMES[kind],
                      "x": round(x, 4), "y": round(y, 4), "w": w, "d": d, "h": h, "z0": z0, "회전": more.pop("회전", 0), **more})

    # 바닥 — 전산실 이중마루, 관제실·전기실 일반 바닥
    add("floor", "F001", sum(HALL) / 2, (0.6 + 12.3) / 2, round(HALL[1] - HALL[0], 3), 11.7, .15, -.15, 이름="전산실 이중마루")
    add("floor", "F002", (0.2 + HALL[0]) / 2, (0.6 + 12.3) / 2, round(HALL[0] - .2, 3), 11.7, .15, -.15, 이름="관제실 바닥")
    add("floor", "F003", (HALL[1] + 51.8) / 2, (0.6 + 12.3) / 2, round(51.8 - HALL[1], 3), 11.7, .15, -.15, 이름="복도·전기실 바닥")

    # 벽 — 바깥 네 벽, 관제실·전기실 칸막이 (문 자리는 비운다)
    walls = [((0, .5), (W, .5)), ((0, 12.4), (W, 12.4)), ((.1, .5), (.1, 12.4)), ((W - .1, .5), (W - .1, 12.4)),
             ((HALL[0], .5), (HALL[0], 9.6)), ((HALL[0], 10.8), (HALL[0], 12.4)),          # 관제실 — 아래쪽 문
             ((.1, 2.6), (HALL[0], 2.6)),                                                 # 관제실 위 복도
             ((HALL[1], .5), (HALL[1], 4.4)), ((HALL[1], 5.6), (HALL[1], 12.4)),          # 오른쪽 — 가운데 문
             ((HALL[1], 7.6), (49.0, 7.6)), ((50.2, 7.6), (W - .1, 7.6))]                 # 전기실 — 문
    for i, ((x0, y0), (x1, y1)) in enumerate(walls, 1):
        horiz = abs(y1 - y0) < 1e-9
        length = round(abs(x1 - x0) if horiz else abs(y1 - y0), 3)
        add("wall", f"W{i:03d}", (x0 + x1) / 2, (y0 + y1) / 2, length if horiz else .2, .2 if horiz else length, H)
    for i, (x, y) in enumerate([(HALL[0], 10.2), (HALL[1], 5.0), (49.6, 7.6)], 1):
        add("door", f"D{i:02d}", x, y, 1.0 if abs(y - 7.6) < 1e-9 else .1, .1 if abs(y - 7.6) < 1e-9 else 1.0, 2.1,
            이름=["관제실 문", "복도 문", "전기실 문"][i - 1])

    # 기둥 — 위쪽 벽의 검은 네모
    for i, px in enumerate(COL_PX, 1):
        add("col", f"C{i:02d}", round(px * KX, 3), 1.0, .6, .6, H)

    # 항온항습기 9대 — 위쪽 벽, 코드 CRAC-0n
    for i, px in enumerate(CRAC_PX, 1):
        add("crac", f"AC{i:02d}", round(px * KX, 3), 1.15, 1.6, .9, 2.0, 이름=f"항온항습기 {i}호", 점=f"CRAC-{i:02d}")

    # 랙 14열 × 10대 — 열 이름은 배치도와 같은 「N열」
    rows = [mx(p) for p in ROW_X]
    for r, x in enumerate(rows, 1):
        for k in range(RACKS):
            add("rack", f"R{r:02d}-{k + 1:02d}", x, round(ROW_Y0 + .3 + k * .6, 3), 1.0, .6, 2.0, 열=f"{r}열")
    # 랙 흡입온도 RACK.RrCc.TEMP — r열의 3~8번째 랙
    for it in items:
        if it["종류"] != "rack":
            continue
        r, k = int(it["id"][1:3]), int(it["id"][4:6])
        if r <= 4 and 3 <= k <= 8:
            it["점"] = f"RACK.R{r}C{k - 2}.TEMP"
            it["이름"] = f"서버 랙 (R{r}C{k - 2})"

    aisles = [(a + b) / 2 for a, b in zip(rows, rows[1:])]

    def to_aisle(x: float) -> float:
        """랙 속(열 가운데 ±0.6 m)이면 가장 가까운 통로 가운데로."""
        if HALL[0] < x < HALL[1] and any(abs(x - rx) < .6 for rx in rows):
            return round(min(aisles, key=lambda a: abs(a - x)), 3)
        return x

    for i, (px, py) in enumerate(TEMP, 1):
        x, y = mx(px), my(py)
        if ROW_Y0 <= y <= ROW_Y0 + RACKS * .6:
            x = to_aisle(x)
        add("s_temp", f"T{i:02d}", x, y, .06, .03, .1, 1.5, 이름=f"{i}구역 온도", 점=f"PLAN.TEMP.{i:02d}")
    for i, x in enumerate(rows, 1):           # 「N열 누수」 — 열 오른쪽 통로 바닥을 따라
        add("s_leak_line", f"LL{i:02d}", round(x + .62, 3), round(ROW_Y0 + RACKS * .3, 3), round(RACKS * .6, 3), .03, .01, 0,
            회전=90, 이름=f"{i}열 누수 감지선", 점=f"PLAN.LEAK.{i:02d}")
    for j, (px, py) in enumerate(LEAK_PT, 15):
        add("s_leak", f"LP{j:02d}", mx(px), my(py), .08, .08, .03, 0, 이름=f"누수 감지기 {j}", 점=f"PLAN.LEAK.{j:02d}")
    for i, px in enumerate(WIND, 1):
        add("s_wind", f"WS{i:02d}", to_aisle(mx(px)), my(WIND_Y), .05, .05, .15, .3, 이름=f"{i}통로 풍속", 점=f"PLAN.WIND.{i:02d}")
    for i, x in enumerate((16.0, 24.0, 32.0, 40.0), 1):
        add("s_smoke", f"SM{i:02d}", x, 6.4, .12, .12, .05, 3.3, 이름=f"연기 감지기 {i}", 점=f"FIRE.{i:02d}")
    add("s_th", "TH01", 43.6, 2.4, .08, .03, .12, 1.5, 이름="3층 실내 온습도", 점="ENV3F")
    # 전기실 — UPS01 과 배터리
    add("ups", "UPS01", 47.6, 10.6, 1.2, .8, 1.95, 이름="1호 UPS", 점="UPS01")
    add("battery", "BT01", 49.7, 10.6, 1.5, .75, 1.8, 이름="1호 UPS 배터리")
    add("battery", "BT02", 49.7, 11.6, 1.5, .75, 1.8, 이름="1호 UPS 배터리")
    return {"판": 2, "방": {"w": W, "d": D, "h": H}, "항목": items,
            "메모": "서울센터 3층 전산실 — 대시보드 「3층 전산실 배치도」(plan_3f.jpg)를 옮긴 근사 배치. 60_monitor_ui/room3d_seoul.py 가 만든다"}


NAMES = {"floor": "바닥 (이중마루) 구역", "wall": "벽", "door": "출입문", "col": "기둥", "crac": "항온항습기",
         "rack": "서버 랙 42U", "s_temp": "온도 센서", "s_leak_line": "누수 감지선", "s_leak": "누수 감지기 (점형)",
         "s_wind": "풍속 센서", "s_smoke": "연기 감지기", "s_th": "온습도 센서", "ups": "UPS", "battery": "배터리 랙"}


def text() -> str:
    return json.dumps(build(), ensure_ascii=False, indent=1) + "\n"


SITES = ("SEOUL", "BUSAN", "DAEJEON", "DAEGU")    # 79차 — 다른 센터 배치는 room3d_centers.py 가 만든다


def index_text() -> str:
    return json.dumps({c: f"room3d_site_{c}.json" for c in SITES}, ensure_ascii=False) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="서울센터 3D 기본 배치 만들기")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    t = text()
    if a.check:
        ok = OUT.exists() and OUT.read_text(encoding="utf-8") == t and \
            INDEX.exists() and INDEX.read_text(encoding="utf-8") == index_text()
        print(("✓ 최신 " if ok else "✗ 옛것 — python3 60_monitor_ui/room3d_seoul.py ") + OUT.name)
        return 0 if ok else 1
    OUT.write_text(t, encoding="utf-8")
    INDEX.write_text(index_text(), encoding="utf-8")
    print(f"✓ {OUT.name} — 항목 {len(build()['항목'])}개")
    return 0


if __name__ == "__main__":
    sys.exit(main())
