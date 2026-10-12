# 3D 상면 화면(static/room3d.html)을 크로미엄으로 열어 보기·게이지·편집기를 시험한다 — 쓰는 법: python3 room3d_check.py <static 폴더> <그림 폴더> (playwright 필요)
import sys, subprocess, time, json, os
from playwright.sync_api import sync_playwright

ST = sys.argv[1]
OUT = sys.argv[2]
os.makedirs(OUT, exist_ok=True)
srv = subprocess.Popen([sys.executable, "-m", "http.server", "8765", "-d", ST],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
실패 = []
def 확인(조건, 말):
    print(("통과 " if 조건 else "실패 ") + 말)
    if not 조건: 실패.append(말)

try:
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        ctx = b.new_context(viewport={"width": 1600, "height": 900}, accept_downloads=True)
        pg = ctx.new_page()
        오류 = []
        pg.on("console", lambda m: m.type in ("error", "warning") and 오류.append(m.text))
        pg.on("pageerror", lambda e: 오류.append(str(e)))
        pg.goto("http://127.0.0.1:8765/room3d.html")
        pg.wait_for_function("window.__room3d", timeout=20000)
        pg.wait_for_timeout(1200)
        pg.screenshot(path=f"{OUT}/01_보기_비스듬히.png")

        def 다옴(ms=300):
            pg.wait_for_timeout(ms); pg.wait_for_function("!window.__room3d.나는중()", timeout=15000); pg.wait_for_timeout(250)
        화면 = lambda id: pg.evaluate("id => window.__room3d.화면(id)", id)
        거리 = lambda: pg.evaluate("window.__room3d.camera.position.distanceTo(window.__room3d.controls.target)")
        목표 = lambda: pg.evaluate("(({x,y,z}) => ({x,y,z}))(window.__room3d.controls.target)")
        고른 = lambda: pg.evaluate("window.__room3d.고른()")
        항목 = lambda id: pg.evaluate("id => window.__room3d.모형().항목.find(it => it.id === id) || null", id)
        개수 = lambda: pg.evaluate("window.__room3d.모형().항목.length")

        # ── 보기 ──
        a = 화면("R230"); d0 = 거리()
        pg.mouse.move(a["x"], a["y"])
        for _ in range(8):
            pg.mouse.wheel(0, -240); pg.wait_for_timeout(120)
        pg.wait_for_timeout(900)
        a2 = 화면("R230"); 밀림 = ((a2["x"] - a["x"]) ** 2 + (a2["y"] - a["y"]) ** 2) ** 0.5
        확인(거리() < d0 * 0.6, f"휠 확대 — 거리 {d0:.1f} → {거리():.1f} m")
        확인(밀림 < 40, f"휠 확대 — 가리킨 랙이 마우스 아래에 남음 (밀림 {밀림:.0f}px)")

        pg.evaluate("window.__room3d.시점들.iso()"); 다옴()
        a = 화면("R100"); pg.mouse.dblclick(a["x"], a["y"]); 다옴()
        t = 목표()
        확인(고른() == ["R100"], f"두 번 누르기 — 고른 것 {고른()}")
        확인(abs(t["x"] - 18.0) < 1.0 and abs(t["z"] - 8.5) < 1.0, f"두 번 누르기 — 목표점 x {t['x']:.1f} · y {t['z']:.1f}")
        확인("R100" in pg.inner_text("#info"), "정보 창에 고른 랙 이름")

        box = pg.locator("#mini").bounding_box(); k = (262 - 12) / 46.0
        pg.mouse.click(box["x"] + 6 + 40 * k, box["y"] + 6 + 21 * k); 다옴()
        t = 목표()
        확인(abs(t["x"] - 40) < 0.6 and abs(t["z"] - 21) < 0.6, f"미니맵 누르기 — 목표점 x {t['x']:.1f} · y {t['z']:.1f}")

        pg.fill("#find", "c1"); pg.press("#find", "Enter"); 다옴()
        확인(len(고른()) == 19, f"찾기 「c1」 — 열 C1 랙 {len(고른())}대")
        pg.fill("#find", "123"); pg.press("#find", "Enter"); 다옴()
        확인(고른() == ["R123"], "찾기 「123」 — R123")
        pg.fill("#find", "ac5"); pg.press("#find", "Enter"); 다옴()
        확인(고른() == ["AC05"], "찾기 「ac5」 — AC05")
        pg.fill("#find", "없는것"); pg.press("#find", "Enter"); pg.wait_for_timeout(200)
        확인("찾지 못했습니다" in pg.inner_text("#info"), "찾기 — 없는 것은 안내")

        pg.mouse.click(800, 30); t0 = 목표()
        pg.keyboard.press("w"); pg.wait_for_timeout(200); t1 = 목표()
        확인(((t1["x"] - t0["x"]) ** 2 + (t1["z"] - t0["z"]) ** 2) ** 0.5 > 0.3, "키보드 W — 앞으로 이동")

        # 게이지
        pg.keyboard.press("Home"); 다옴()
        읽기 = lambda: pg.evaluate("""() => { const {camera, controls} = window.__room3d; const t = controls.target;
          const c = camera.position.clone().sub(t), d = c.length();
          return {x: t.x, y: t.z, z: t.y, 거리: d, 방위: Math.atan2(c.x, c.z) * 180 / Math.PI}; }""")
        줄 = lambda n: pg.locator("#g_rows .g").nth(n)
        v0 = 읽기(); 줄(0).locator("button").nth(1).click(); pg.wait_for_timeout(150); v1 = 읽기()
        확인(abs(v1["x"] - v0["x"] - 0.1) < 1e-3, f"게이지 X ▶ — +{v1['x'] - v0['x']:.3f} m")
        pg.select_option("#g_step", "0.1")
        줄(1).locator("button").nth(0).click(); pg.wait_for_timeout(150); v2 = 읽기()
        확인(abs(v2["y"] - v1["y"] + 0.01) < 1e-4, f"게이지 Y ◀ (아주 섬세) — {v2['y'] - v1['y']:+.4f} m")
        r = 줄(3).locator("input[type=range]")
        r.evaluate("e => { e.value = 30; e.dispatchEvent(new Event('input')); }"); pg.wait_for_timeout(150)
        확인(abs(읽기()["방위"] - 30) < 1e-3, f"게이지 회전 막대 30° — {읽기()['방위']:.2f}°")
        pg.select_option("#g_step", "1")
        pg.click("#v_top"); 다옴(); pg.screenshot(path=f"{OUT}/02_보기_위에서.png")
        pg.click("#v_iso"); 다옴()

        # ── 편집기 ──
        pg.click("#toEdit"); pg.wait_for_timeout(1200)
        확인(pg.evaluate("document.body.classList.contains('편집')"), "편집 모드로 바뀜")
        pg.screenshot(path=f"{OUT}/10_편집_평면.png")
        타일 = pg.locator("#lib .타일")
        이름들 = 타일.all_inner_texts()
        확인(타일.count() >= 28, f"장비 라이브러리 {타일.count()}종")
        for 꼭 in ["서버 랙", "항온항습기", "스탠드 에어컨", "천장형 에어컨", "벽걸이 에어컨", "기류(플로우) 화살표", "온도 센서",
                   "습도 센서", "온습도 센서", "누수 감지선", "연기 감지기", "CCTV", "UPS", "벽", "기둥", "출입문", "바닥"]:
            확인(any(꼭 in n for n in 이름들), f"라이브러리에 「{꼭}」")

        def 평(x, y):
            return pg.evaluate("""([x, y]) => { const r = document.getElementById('stage').getBoundingClientRect();
              const [a, b] = window.__room3d.평면에서화면(x, y); return [r.left + a, r.top + b]; }""", [x, y])

        # 놓기 — 타일을 누르고 빈 바닥을 누른다
        n0 = 개수()
        pg.locator("#lib .타일[data-k=rack]").click()
        pg.mouse.click(*평(25.0, 15.0)); pg.wait_for_timeout(300)
        r292 = 항목("R292")
        확인(r292 is not None and 개수() == n0 + 1, f"랙 놓기 — R292 생김 {r292 and (r292['x'], r292['y'])}")
        확인(r292 and abs(r292["x"] - 24.9) < 1e-6 and abs(r292["y"] - 14.9) < 1e-6, "놓은 랙이 바닥타일 격자에 맞음 (24.9, 14.9)")
        확인(고른() == ["R292"], "놓은 것이 골라짐")

        # 끌어 옮기기 — 1.2 m (격자 600 mm)
        s = 평(24.9, 14.9); e = 평(26.1, 14.9)
        pg.mouse.move(*s); pg.mouse.down(); pg.mouse.move(e[0], e[1], steps=8); pg.mouse.up(); pg.wait_for_timeout(200)
        확인(abs(항목("R292")["x"] - 26.1) < 1e-6, f"끌어 옮기기 — x {항목('R292')['x']}")

        # 화살표 키 1 cm · Shift 10 cm
        pg.keyboard.press("ArrowRight"); pg.keyboard.press("Shift+ArrowRight"); pg.wait_for_timeout(150)
        확인(abs(항목("R292")["x"] - 26.21) < 1e-6, f"화살표 1 cm + Shift 10 cm — x {항목('R292')['x']}")
        pg.keyboard.press("Control+z"); pg.wait_for_timeout(150)
        확인(abs(항목("R292")["x"] - 26.1) < 1e-6, f"실행 취소 — x {항목('R292')['x']} (화살표 둘이 한 번에)")
        pg.keyboard.press("Control+Shift+z"); pg.wait_for_timeout(150)
        확인(abs(항목("R292")["x"] - 26.21) < 1e-6, "다시 실행")

        # 옵션 막대 숫자
        f = pg.locator("#optbar input[data-k=w]"); f.fill("0.8"); f.press("Enter"); pg.wait_for_timeout(150)
        확인(abs(항목("R292")["w"] - 0.8) < 1e-9, "옵션 막대 폭 0.8 m")

        # 크기 손잡이 — 오른쪽 가운데 손잡이를 0.4 m 끌기 (Ctrl = 칸 맞춤 없이)
        it = 항목("R292"); hx = it["x"] + it["w"] / 2
        s = 평(hx, it["y"]); e = 평(hx + 0.4, it["y"])
        pg.mouse.move(*s); pg.mouse.down(); pg.mouse.move(e[0], e[1], steps=6); pg.mouse.up(); pg.wait_for_timeout(150)
        it2 = 항목("R292")
        확인(abs(it2["w"] - 1.2) < 0.02 and abs((it2["x"] - it2["w"] / 2) - (it["x"] - it["w"] / 2)) < 1e-6,
             f"크기 손잡이 — 폭 {it2['w']} (왼쪽 끝은 그대로)")

        # 회전 — 옵션 막대
        f = pg.locator("#optbar input[data-k=회전]"); f.fill("90"); f.press("Enter"); pg.wait_for_timeout(150)
        확인(항목("R292")["회전"] == 90, "회전 90°")
        pg.keyboard.press("e"); pg.wait_for_timeout(100)
        확인(항목("R292")["회전"] == -180 or 항목("R292")["회전"] == 180, f"E 키 90° 더 — {항목('R292')['회전']}°")

        # 복사·붙여넣기·Alt 끌기 복제·지우기
        n1 = 개수()
        pg.keyboard.press("Control+c"); pg.keyboard.press("Control+v"); pg.wait_for_timeout(150)
        확인(개수() == n1 + 1 and 고른()[0] != "R292", f"복사·붙여넣기 — 새 ID {고른()}")
        pg.keyboard.press("Delete"); pg.wait_for_timeout(150)
        확인(개수() == n1, "지우기")
        it = 항목("R292"); s = 평(it["x"], it["y"]); e = 평(it["x"], it["y"] + 1.8)
        pg.keyboard.down("Alt"); pg.mouse.move(*s); pg.mouse.down(); pg.mouse.move(e[0], e[1], steps=8); pg.mouse.up(); pg.keyboard.up("Alt")
        pg.wait_for_timeout(200)
        확인(개수() == n1 + 1 and abs(항목("R292")["y"] - it["y"]) < 1e-9, f"Alt 끌기 복제 — 원본 그대로, 복제본 {고른()}")

        # 벽 그리기
        pg.keyboard.press("b")
        s = 평(30.0, 14.0); e = 평(33.0, 14.0)
        pg.mouse.move(*s); pg.mouse.down(); pg.mouse.move(e[0], e[1], steps=6); pg.mouse.up(); pg.wait_for_timeout(200)
        벽 = pg.evaluate("window.__room3d.고른().map(id => window.__room3d.모형().항목.find(i => i.id === id))")
        확인(len(벽) == 1 and 벽[0]["종류"] == "wall" and abs(벽[0]["w"] - 3.0) < 1e-6 and 벽[0]["회전"] == 0, f"벽 그리기 — {벽[0]['id'] if 벽 else None} 3 m")

        # 사각 선택 — 열 C1 만 감싼다
        pg.keyboard.press("m")
        s = 평(12.9, 5.7); e = 평(13.58, 17.2)
        pg.mouse.move(*s); pg.mouse.down(); pg.mouse.move(e[0], e[1], steps=6); pg.mouse.up(); pg.wait_for_timeout(200)
        확인(len(고른()) == 19, f"사각 선택 — {len(고른())}개 (열 C1)")
        pg.screenshot(path=f"{OUT}/11_편집_사각선택.png")

        # 레이어 잠금 — 잠근 랙은 눌러도 안 골라진다
        pg.keyboard.press("v"); pg.keyboard.press("Control+d")
        pg.locator("#layers .층").nth(0).locator("button").nth(1).click(); pg.wait_for_timeout(200)
        pg.mouse.click(*평(18.0, 8.5)); pg.wait_for_timeout(150)
        확인(고른() == [], "잠근 랙 레이어는 고를 수 없음")
        pg.locator("#layers .층").nth(0).locator("button").nth(1).click(); pg.wait_for_timeout(200)
        pg.mouse.click(*평(18.0, 8.5)); pg.wait_for_timeout(150)
        확인(고른() == ["R100"], f"잠금 풀면 다시 고름 — {고른()}")

        # 센서 끌어 놓기 (HTML5 끌기)
        n2 = 개수()
        st = pg.locator("#stage").bounding_box(); 자리 = 평(25.0, 12.0)
        pg.locator("#lib .타일[data-k=s_temp]").drag_to(pg.locator("#stage"), target_position={"x": 자리[0] - st["x"], "y": 자리[1] - st["y"]})
        pg.wait_for_timeout(300)
        확인(개수() == n2 + 1 and 항목("T01") is not None, f"온도 센서 끌어 놓기 — T01 {항목('T01') and (항목('T01')['x'], 항목('T01')['y'])}")
        pg.screenshot(path=f"{OUT}/12_편집_센서.png")

        # 작업 내역
        내역 = pg.evaluate("window.__room3d.내역()")
        확인(len(내역) > 8 and 내역[0] == "열기", f"작업 내역 {len(내역)}줄")

        # 3D 로 보기
        pg.keyboard.press("3"); 다옴(); pg.wait_for_timeout(400)
        pg.screenshot(path=f"{OUT}/13_편집_3D.png")
        pg.keyboard.press("2"); pg.wait_for_timeout(400)

        # 저장 → 다시 열어도 남는다
        확인(not pg.evaluate("window.__room3d.저장됨()"), "고치면 「저장 안 됨」")
        pg.keyboard.press("Control+s"); pg.wait_for_timeout(200)
        확인(pg.evaluate("window.__room3d.저장됨()") and pg.evaluate("!!localStorage.getItem('fms.room3d.layout.v2')"), "Ctrl+S 저장")
        with pg.expect_download() as dl:
            pg.click("#menus .메뉴:nth-child(1) > button"); pg.click("text=JSON 파일로 내려받기")
        경로 = dl.value.path(); 내려 = json.load(open(경로, encoding="utf-8"))
        확인(내려["판"] == 2 and len(내려["항목"]) == 개수(), f"JSON 내려받기 — {len(내려['항목'])}개")
        pg.click("#toView"); pg.wait_for_timeout(800)
        pg.reload(); pg.wait_for_function("window.__room3d", timeout=20000); pg.wait_for_timeout(800)
        확인(항목("R292") is not None and 항목("T01") is not None, "다시 열어도 저장한 배치 (R292·T01)")
        확인("브라우저에 저장된 배치" in pg.inner_text("#source"), "보기 화면에 「브라우저에 저장된 배치」")
        pg.fill("#find", "r292"); pg.press("#find", "Enter"); 다옴()
        pg.screenshot(path=f"{OUT}/14_보기_새랙.png")

        # JSON 열기
        pg.click("#toEdit"); pg.wait_for_timeout(800)
        내려["항목"] = 내려["항목"][:10]
        json.dump(내려, open(f"{OUT}/작은배치.json", "w", encoding="utf-8"), ensure_ascii=False)
        pg.set_input_files("#fileIn", f"{OUT}/작은배치.json"); pg.wait_for_timeout(400)
        확인(개수() == 10, f"JSON 파일 열기 — {개수()}개")
        pg.keyboard.press("Control+z"); pg.wait_for_timeout(200)
        확인(개수() > 600, "파일 열기도 실행 취소됨")
        pg.evaluate("localStorage.clear()")

        확인(not 오류, f"콘솔 오류·경고 {len(오류)}건 {오류[:3]}")
        b.close()
finally:
    srv.terminate()
print("실패", len(실패))
sys.exit(1 if 실패 else 0)
