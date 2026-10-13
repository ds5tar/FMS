# 부산·대전·대구센터의 3D 기본 배치(static/room3d_site_<현장>.json)를 그 현장 센서로 만든다 — 79차
#
# 왜 (2026-10-13, 79차 사용자 「모든 센터를 지금한것처럼 서울센터처럼 해라」)
#   서울센터만 기본 배치(room3d_seoul.py)가 있어, 다른 센터는 3D 상면을 열면 센서 값 없는 예시 도면이 나왔다.
#   센터마다 작은 전산실(벽·문·이중마루·항온항습기·랙 열·UPS)을 두고, 그 센터 센서를 모두 장비·센서에 붙인다.
#   도면이 없는 근사 배치다 — 편집에서 실제에 맞게 고쳐 저장하면 서버 배치가 기본 배치보다 먼저다.
#     · 부산 BS.*  — UPS01(배터리 전압·부하율) → UPS, BS.ENV(실내 온도·습도) → 온습도 센서
#     · 대전 DJ.*  — 위 둘 + DJ.CRAC01(환기온도·습도) → 항온항습기, DJ.LEAK01(감지·위치) → 그 둘레 10 m 누수 감지선
#     · 대구 GW-DAEGU.* (클라이브 자동 등록) — D1.S0 온도, D1.S1 습도, 출입문(D1.S3 상태·D1.S4 마지막 열림·unlock)
#   코드가 FMS 에 없으면 3D 는 그 항목에 표를 안 띄우고 알람 창에 「코드를 못 찾은 항목 N개」 로만 알린다(78차).
#
#   python3 room3d_centers.py           # 세 파일을 다시 만든다
#   python3 room3d_centers.py --check   # 지금 파일이 최신인지

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from room3d_seoul import INDEX, index_text

HERE = Path(__file__).resolve().parent
H = 3.6


def room(이름: str, w: float, d: float, door_x: float) -> tuple[list[dict], callable]:
    """바깥 벽 네 개(아래 벽에 문), 이중마루 — 항목 목록과 add 를 돌려준다."""
    items: list[dict] = []

    def add(kind, iid, x, y, w_, d_, h, z0=0.0, 이름_=None, **more):
        items.append({"id": iid, "종류": kind, "이름": 이름_, "x": round(x, 4), "y": round(y, 4),
                      "w": w_, "d": d_, "h": h, "z0": z0, "회전": more.pop("회전", 0), **more})

    add("floor", "F001", w / 2, d / 2, w, d, .15, -.15, f"{이름} 이중마루")
    t = .2
    add("wall", "W001", w / 2, t / 2, w, t, H, 이름_="벽")
    add("wall", "W002", t / 2, d / 2, t, d, H, 이름_="벽")
    add("wall", "W003", w - t / 2, d / 2, t, d, H, 이름_="벽")
    left = door_x - .5                                         # 아래 벽 — 문 자리 1 m 를 비운다
    add("wall", "W004", left / 2, d - t / 2, round(left, 3), t, H, 이름_="벽")
    add("wall", "W005", (door_x + .5 + w) / 2, d - t / 2, round(w - door_x - .5, 3), t, H, 이름_="벽")
    add("door", "D01", door_x, d - t / 2, 1.0, .1, 2.1, 이름_="출입문")
    return items, add


def racks(add, xs: list[float], y0: float, n: int, 열이름: list[str]) -> None:
    """열마다 n 대 — 서울과 같이 세로(y)로 늘어선 열, 랙 1.0×0.6 m."""
    for r, (x, 열) in enumerate(zip(xs, 열이름), 1):
        for k in range(n):
            add("rack", f"R{r:02d}-{k + 1:02d}", x, round(y0 + .3 + k * .6, 3), 1.0, .6, 2.0, 이름_="서버 랙 42U", 열=열)


def busan() -> dict:
    W, D = 14.0, 9.0
    items, add = room("부산센터 전산실", W, D, 1.6)
    for i, x in enumerate((4.0, 9.0), 1):
        add("crac", f"AC{i:02d}", x, .75, 1.6, .9, 2.0, 이름_=f"항온항습기 {i}호")
    racks(add, [3.5, 5.6, 7.7, 9.8], 2.4, 8, ["A열", "B열", "C열", "D열"])
    add("ups", "UPS01", 12.6, 3.0, 1.2, .8, 1.95, 이름_="부산 UPS01", 점="BS.UPS01")
    add("battery", "BT01", 12.6, 4.4, 1.5, .75, 1.8, 이름_="UPS01 배터리")
    add("s_th", "TH01", 6.6, D - .25, .08, .03, .12, 1.5, "부산 전산실 온습도", 점="BS.ENV")
    return {"판": 2, "방": {"w": W, "d": D, "h": H}, "항목": items,
            "메모": "부산센터 전산실 — 도면 없이 센서(BS.*)로 만든 근사 배치. 60_monitor_ui/room3d_centers.py 가 만든다"}


def daejeon() -> dict:
    W, D = 14.0, 10.0
    items, add = room("대전센터 전산실", W, D, 1.6)
    # 항온항습기 2600×900 — 둘레 10 m 감지선이 37.5 cm 띄워 돈다(75차). 뒤 벽 앞 3 cm 에 감지선이 오게 놓는다
    cw, cd = 2.6, .9
    lw, ld = round(cw + .75, 3), round(cd + .75, 3)
    cy = round(.2 + .03 + ld / 2, 3)
    add("crac", "AC01", 4.2, cy, cw, cd, 2.0, 이름_="대전 CRAC-01 항온항습기", 점="DJ.CRAC01")
    add("s_leak_loop", "LR01", 4.2, cy, lw, ld, .01, 0, "항온항습기 둘레 누수 감지선 10 m", 점="DJ.LEAK01",
        메모="거리감지형 — 길이 10 m. 누수 위치는 왼쪽 위 모서리에서 시계 방향으로 잰 거리")
    add("crac", "AC02", 9.6, .75, 1.6, .9, 2.0, 이름_="항온항습기 2호")
    racks(add, [3.5, 5.6, 7.7, 9.8], 3.0, 8, ["A열", "B열", "C열", "D열"])
    add("ups", "UPS01", 12.6, 3.6, 1.2, .8, 1.95, 이름_="대전 UPS01", 점="DJ.UPS01")
    add("battery", "BT01", 12.6, 5.0, 1.5, .75, 1.8, 이름_="UPS01 배터리")
    add("s_th", "TH01", 6.6, D - .25, .08, .03, .12, 1.5, "대전 전산실 온습도", 점="DJ.ENV")
    return {"판": 2, "방": {"w": W, "d": D, "h": H}, "항목": items,
            "메모": "대전센터 전산실 — 도면 없이 센서(DJ.*)로 만든 근사 배치. 60_monitor_ui/room3d_centers.py 가 만든다"}


def daegu() -> dict:
    W, D = 10.0, 7.0
    items, add = room("대구센터 전산실", W, D, 1.4)
    add("crac", "AC01", 6.0, .75, 1.6, .9, 2.0, 이름_="항온항습기 1호")
    racks(add, [4.0, 6.1], 2.2, 6, ["A열", "B열"])
    add("s_temp", "T01", 8.6, 3.2, .06, .03, .1, 1.5, "대구 전산실 온도", 점="GW-DAEGU.D1.S0")
    add("s_humi", "H01", 8.6, 4.4, .06, .03, .1, 1.5, "대구 전산실 습도", 점="GW-DAEGU.D1.S1")
    # 출입문 센서 셋 — 문 오른쪽 벽에 나란히 (상태 · 마지막 열림 · 잠금 풀기)
    for i, (code, 이름) in enumerate((("GW-DAEGU.D1.S3", "출입문 상태"), ("GW-DAEGU.D1.S4", "출입문 마지막 열림"),
                                      ("GW-DAEGU.unlock", "출입문 잠금 풀기")), 1):
        add("s_door", f"DS{i:02d}", round(2.2 + (i - 1) * .5, 3), D - .25, .05, .03, .1, 2.0, 이름, 점=code)
    return {"판": 2, "방": {"w": W, "d": D, "h": H}, "항목": items,
            "메모": "대구센터 전산실 — 도면 없이 클라이브 게이트웨이 센서(GW-DAEGU.*)로 만든 근사 배치. 60_monitor_ui/room3d_centers.py 가 만든다"}


CENTERS = {"BUSAN": busan, "DAEJEON": daejeon, "DAEGU": daegu}


def out(code: str) -> Path:
    return HERE / "static" / f"room3d_site_{code}.json"


def text(code: str) -> str:
    return json.dumps(CENTERS[code](), ensure_ascii=False, indent=1) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="부산·대전·대구센터 3D 기본 배치 만들기")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        bad = [c for c in CENTERS if not out(c).exists() or out(c).read_text(encoding="utf-8") != text(c)]
        if not INDEX.exists() or INDEX.read_text(encoding="utf-8") != index_text():
            bad.append(INDEX.name)
        print("✓ 최신 " + ", ".join(out(c).name for c in CENTERS) if not bad else
              "✗ 옛것 — python3 60_monitor_ui/room3d_centers.py · " + ", ".join(bad))
        return 0 if not bad else 1
    for c in CENTERS:
        out(c).write_text(text(c), encoding="utf-8")
        print(f"✓ {out(c).name} — 항목 {len(CENTERS[c]()['항목'])}개")
    INDEX.write_text(index_text(), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
