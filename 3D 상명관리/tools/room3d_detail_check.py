# 3D 상면 설비 모양 시험 (103차) — 세부 부품·요철 질감·환경 반사·색 보정·무료 라이선스 glTF 모델 — 쓰는 법: python3 room3d_detail_check.py <static 폴더> <그림 폴더>
#
# 왜 (2026-10-15, 사용자 「설비의 모양이 좀 더 디테일하고 정교하게 만들 더 좋은 방법을 찾아보고 여러가지 안을 제시후 실행」
#   → ① 부품 붙이기 ② 요철 질감·금속 반사 ③ 조명·색 보정 ④ 무료 라이선스 glTF 모델 불러오기 를 골랐다)
#   static 을 임시 폴더에 복사해 시험용 배치(종류마다 하나)와 시험용 glb 모델·모델 목록을 넣고 연다. 저장소의 static 은 건드리지 않는다.

import json
import math
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time

from playwright.sync_api import sync_playwright

ST = sys.argv[1]
OUT = sys.argv[2]
os.makedirs(OUT, exist_ok=True)
실패 = []


def 확인(조건, 말):
    print(("통과 " if 조건 else "실패 ") + 말)
    if not 조건:
        실패.append(말)


def 상자glb(색=(0.2, 0.6, 0.9, 1.0)) -> bytes:
    """시험용 glb — 노드 두 개(자식은 옮기고 키움), 2×1×4 상자 하나(uint16 색인), 기본색. 앞(+z)으로 긴 상자."""
    p = [(-1, -.5, -2), (1, -.5, -2), (1, .5, -2), (-1, .5, -2), (-1, -.5, 2), (1, -.5, 2), (1, .5, 2), (-1, .5, 2)]
    idx = [0, 2, 1, 0, 3, 2, 4, 5, 6, 4, 6, 7, 0, 1, 5, 0, 5, 4, 3, 7, 6, 3, 6, 2, 0, 4, 7, 0, 7, 3, 1, 2, 6, 1, 6, 5]
    pos = b"".join(struct.pack("<3f", *v) for v in p)
    ind = b"".join(struct.pack("<H", i) for i in idx)
    ind += b"\0" * (-len(ind) % 4)
    bin_ = pos + ind
    gl = {"asset": {"version": "2.0"}, "scene": 0, "scenes": [{"nodes": [0]}],
          "nodes": [{"children": [1], "translation": [5, 0, 0]}, {"mesh": 0, "scale": [2, 2, 2]}],
          "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "indices": 1, "material": 0}]}],
          "materials": [{"pbrMetallicRoughness": {"baseColorFactor": list(색), "metallicFactor": .3, "roughnessFactor": .6}}],
          "buffers": [{"byteLength": len(bin_)}],
          "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": len(pos)},
                          {"buffer": 0, "byteOffset": len(pos), "byteLength": len(idx) * 2}],
          "accessors": [{"bufferView": 0, "componentType": 5126, "count": 8, "type": "VEC3",
                         "min": [-1, -.5, -2], "max": [1, .5, 2]},
                        {"bufferView": 1, "componentType": 5123, "count": len(idx), "type": "SCALAR"}]}
    js = json.dumps(gl).encode()
    js += b" " * (-len(js) % 4)
    body = struct.pack("<II", len(js), 0x4E4F534A) + js + struct.pack("<II", len(bin_), 0x004E4942) + bin_
    return struct.pack("<III", 0x46546C67, 2, 12 + len(body)) + body


tmp = tempfile.mkdtemp(prefix="r3d_detail_")
st = os.path.join(tmp, "static")
shutil.copytree(ST, st, ignore=shutil.ignore_patterns("demo*.html", "*.png", "*.jpg"))
os.makedirs(os.path.join(st, "models"), exist_ok=True)
open(os.path.join(st, "models", "ups_test.glb"), "wb").write(상자glb())
open(os.path.join(st, "models", "battery_nc.glb"), "wb").write(상자glb((.9, .2, .2, 1)))
open(os.path.join(st, "models", "rack_vertiv.glb"), "wb").write(상자glb((.1, .1, .1, 1)))
json.dump({"models": [
    {"종류": "ups", "file": "models/ups_test.glb", "license": "CC0-1.0", "author": "시험", "source": "room3d_detail_check.py"},
    {"종류": "battery", "file": "models/battery_nc.glb", "license": "CC-BY-NC-4.0", "author": "시험", "source": "비영리 전용 — 쓰면 안 됨"},
    {"종류": "rack", "제조사": "Vertiv", "모델": "VR3100", "file": "models/rack_vertiv.glb", "license": "CC-BY-4.0", "author": "시험 작성자"}]},
    open(os.path.join(st, "room3d_models.json"), "w", encoding="utf-8"), ensure_ascii=False)

# 종류마다 하나 — 하나는 돌려 둔다(부품도 같이 돌아야 한다). 크기는 room3d.html 장비 기본값
크기 = {"rack": (.6, 1.0, 2.0), "rack_net": (.8, 1.0, 2.0), "crac": (2.6, .9, 2.0), "inrow": (.3, 1.2, 2.0), "ups": (1.2, .8, 1.95),
      "battery": (1.5, .75, 1.8), "panel": (.8, .4, 1.8), "ac_stand": (.6, .4, 1.85), "door": (1.0, .1, 2.1)}
배치 = {"판": 2, "방": {"w": 14, "d": 8, "h": 3.6}, "항목": []}
for i, (종, x, y, 회전) in enumerate([("rack", 1.5, 2, 0), ("rack_net", 3, 2, 0), ("crac", 6, 1.5, 0), ("inrow", 9, 2, 0),
                                      ("ups", 11.5, 2, 0), ("battery", 2, 5.5, 0), ("panel", 5, 5.5, 0),
                                      ("ac_stand", 7, 5.5, 0), ("door", 9, 7.5, 0), ("rack", 12, 5.5, 90), ("rack", 13, 2, 0)]):
    w, d, h = 크기[종]
    배치["항목"].append({"id": f"X{i}", "종류": 종, "이름": 종, "x": x, "y": y, "w": w, "d": d, "h": h, "z0": 0, "회전": 회전})
배치["항목"][1].update({"제조사": "APC", "모델": "NetShelter SX"})           # 모델 파일 없음 → 이름판
배치["항목"][10].update({"제조사": "vertiv", "모델": "VR-3100"})           # 대소문자·하이픈 달라도 같은 모델
json.dump(배치, open(os.path.join(OUT, "설비모양배치.json"), "w", encoding="utf-8"), ensure_ascii=False)

srv = subprocess.Popen([sys.executable, "-m", "http.server", "8767", "-d", st],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
try:
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        pg = b.new_context(viewport={"width": 1600, "height": 900}).new_page()
        pg.set_default_timeout(90000)
        오류 = []
        pg.on("console", lambda m: m.type in ("error", "warning") and 오류.append(m.text))
        pg.on("pageerror", lambda e: 오류.append(str(e)))
        pg.goto("http://127.0.0.1:8767/room3d.html")
        pg.wait_for_function("window.__room3d", timeout=20000)
        pg.wait_for_timeout(800)

        # ── ③ 색 보정 · ② 환경 반사 ──
        r = pg.evaluate("window.__room3d.렌더정보()")
        확인(r["톤"] == "Neutral" and r["노멀"], f"색 보정(Neutral 톤매핑)·랙 요철 질감 — {r}")
        # 반사 — 그래픽 카드 없이 그리는 창(이 시험의 SwiftShader)에서는 처음엔 끄고, 체크로 켠다
        확인(r["소프트웨어"] and not r["환경"] and not pg.is_checked("#t_hq"), f"CPU 로 그리는 창 — 반사는 처음엔 끔 {r}")
        pg.check("#t_hq"); 확인(pg.evaluate("window.__room3d.렌더정보().환경"), "「반사 (고화질)」 를 켜면 환경 반사")
        pg.uncheck("#t_hq"); 확인(not pg.evaluate("window.__room3d.렌더정보().환경"), "끄면 다시 반사 없음")

        # 시험 배치를 파일로 연다 (종류마다 하나)
        pg.click("#toEdit"); pg.wait_for_timeout(600)
        pg.set_input_files("#fileIn", f"{OUT}/설비모양배치.json"); pg.wait_for_timeout(800)
        확인(pg.evaluate("window.__room3d.모형().항목.length") == 11, "시험 배치 열기 — 11개")

        # ── ① 부품 ── 종류마다 부품이 붙고, 몸체와 같은 자리·크기(조금 튀어나온 만큼만 크다)
        최소 = {"rack": 12, "rack_net": 12, "crac": 10, "inrow": 6, "battery": 6, "panel": 8, "ac_stand": 5, "door": 4}
        for i, 종 in enumerate(["rack", "rack_net", "crac", "inrow", "ups", "battery", "panel", "ac_stand", "door", "rack"]):
            b_ = pg.evaluate("id => window.__room3d.부품(id)", f"X{i}")
            if 종 == "ups":      # 무료 라이선스(CC0) 모델이 있는 종류 — 부품 대신 모델 (아래에서 따로 본다)
                continue
            if not b_:
                확인(False, f"{종} X{i} 부품 없음"); continue
            몸, 붙 = b_["몸"], b_["부품"]
            넘침 = max(max(몸["min"][k] - 붙["min"][k], 붙["max"][k] - 몸["max"][k]) for k in range(3))     # 몸체 밖으로 나온 만큼
            한 = .09 if 종 == "door" else .05          # 출입문은 문틀이 문짝 둘레(벽 속)로 나온다
            확인(b_["조각"] >= 최소[종] and 넘침 < 한,
                 f"{종} X{i} 부품 {b_['조각']}개 · 재질 {b_['재질']}가지 · 몸체 밖으로 {넘침 * 100:.1f} cm (회전 {b_['회전']}°)")
        # 앞면 — 손잡이(재질 1)가 앞·뒤로 튀어나오고 옆으로는 안 나간다
        앞 = pg.evaluate("id => window.__room3d.부품(id).손잡이", "X0")
        확인(앞 and 앞["앞뒤"] > .01 and 앞["옆"] < .005, f"랙 손잡이가 앞·뒤 문에 — 앞뒤로 {앞 and 앞['앞뒤'] * 100:.1f} cm, 옆으로 {앞 and 앞['옆'] * 100:.1f} cm")
        돌린 = pg.evaluate("id => window.__room3d.부품(id).손잡이", "X9")
        확인(돌린 and 돌린["앞뒤"] > .01 and 돌린["옆"] < .005, "90° 돌린 랙도 손잡이가 앞·뒤 문에")
        # 고르기는 몸체만 — 부품을 눌러도 그 설비
        확인(pg.evaluate("window.__room3d.부품광선('X0')") == "X0", "부품 쪽을 눌러도 그 설비가 골라짐")
        # 숨기면 부품도 숨는다 (몸체의 자식)
        확인(pg.evaluate("(() => { const R = window.__room3d; R.보이기('랙', false); const v = R.부품보임('X0'); R.보이기('랙', true); return v; })()") is False,
             "랙 층을 끄면 부품도 안 보임")

        # ── ④ glTF 모델 ── CC0 은 쓰고, 비영리(NC)는 안 쓴다
        기다림 = pg.wait_for_function("window.__room3d.모델정보('ups') && window.__room3d.모델정보('ups').상태 !== '읽는 중'", timeout=20000)
        u = pg.evaluate("window.__room3d.모델정보('ups')")
        bt = pg.evaluate("window.__room3d.모델정보('battery')")
        확인(u["상태"] == "씀" and u["라이선스"] == "CC0-1.0", f"CC0 모델은 씀 — {u}")
        확인(bt["상태"] == "라이선스 안 맞음", f"비영리(CC-BY-NC) 모델은 안 씀 — {bt}")
        m = pg.evaluate("window.__room3d.모델붙음('X4')")
        확인(m and m["매시"] == 1 and abs(m["크기"][0] - 1.2) < .02 and abs(m["크기"][1] - .8) < .02 and abs(m["크기"][2] - 1.95) < .02,
             f"UPS 에 모델이 붙고 설비 크기(1.2 × 0.8 × 1.95 m)에 맞춤 — {m}")
        확인(pg.evaluate("window.__room3d.부품('X5') !== null"), "모델을 못 쓰는 배터리는 그대로 부품 모양")
        확인(pg.evaluate("window.__room3d.부품광선('X4')") == "X4", "모델을 단 UPS 도 눌러서 골라짐")
        # 제조사·모델명 — 같은 실물 모델이 있으면 그것, 없으면 부품 모양 + 이름판 (103차 사용자 「회사와 모델명을 추가하면 거의 실사로」)
        v = pg.evaluate("window.__room3d.모델붙음('X10')")
        확인(v is not None and pg.evaluate("window.__room3d.부품('X10')") is None, f"Vertiv VR3100 랙 → 그 실물 모델 (부품 대신) {v}")
        확인(pg.evaluate("window.__room3d.모델붙음('X0')") is None and pg.evaluate("window.__room3d.부품('X0') !== null"),
             "제조사 없는 랙은 부품 모양 (랙 기본 모델 없음)")
        판글 = pg.evaluate("window.__room3d.이름판('X1')")
        확인(판글 == "APC NetShelter SX", f"모델 파일 없는 APC 랙 → 이름판 {판글}")
        확인("Vertiv VR3100: 시험 작성자 · CC-BY-4.0" in pg.inner_text("#credits"), f"CC-BY 출처 표시 — {pg.inner_text('#credits')}")
        # 속성 창에서 제조사·모델명을 적으면 바로 바뀐다
        pg.evaluate("window.__room3d.고르기(['X0'])"); pg.wait_for_timeout(300)
        이름들 = pg.evaluate("[...document.querySelectorAll('#props .속 > span')].map(x => x.textContent)")
        확인("제조사" in 이름들 and "모델명" in 이름들, f"속성에 제조사·모델명 칸 {이름들}")
        def 적기(이름, 값):
            pg.evaluate("""([n, v]) => { const L = [...document.querySelectorAll('#props .속 > span')].find(l => l.textContent === n);
              const i = L.nextElementSibling; i.value = v; i.dispatchEvent(new Event('change', {bubbles: true})); }""", [이름, 값])
            pg.wait_for_timeout(300)
        적기("제조사", "Vertiv"); 적기("모델명", "VR3100")
        확인(pg.evaluate("window.__room3d.모델붙음('X0') !== null"), "속성에 Vertiv VR3100 을 적으면 그 실물 모델로 바뀜")
        적기("모델명", "VR3300")
        확인(pg.evaluate("window.__room3d.모델붙음('X0') === null && window.__room3d.이름판('X0') === 'Vertiv VR3300'"), "없는 모델명이면 부품 모양 + 이름판")
        for 허용 in ("CC0-1.0", "CC-BY-4.0", "MIT"):
            확인(pg.evaluate("l => window.__room3d.모델허용(l)", 허용), f"허용 라이선스 {허용}")
        for 막음 in ("CC-BY-NC-4.0", "CC-BY-ND-4.0", "Sketchfab Standard", "", None):
            확인(not pg.evaluate("l => window.__room3d.모델허용(l)", 막음), f"막는 라이선스 {막음!r}")

        pg.click("#toView"); pg.wait_for_timeout(800)
        pg.evaluate("window.__room3d.가까이('X0')"); pg.wait_for_timeout(1500)
        pg.screenshot(path=f"{OUT}/설비_랙.png")
        pg.evaluate("window.__room3d.가까이('X2')"); pg.wait_for_timeout(1500)
        pg.screenshot(path=f"{OUT}/설비_항온항습기.png")
        pg.evaluate("window.__room3d.시점들.iso()"); pg.wait_for_timeout(1500)
        pg.screenshot(path=f"{OUT}/설비_전체.png")
        확인(not 오류, f"콘솔 오류·경고 {len(오류)}건 {오류[:3]}")
        b.close()
finally:
    srv.terminate()
    shutil.rmtree(tmp, ignore_errors=True)
print("실패", len(실패))
sys.exit(1 if 실패 else 0)
