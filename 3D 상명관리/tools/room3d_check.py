# 3D 상면 화면(static/room3d.html)을 크로미엄으로 열어 보기·게이지·실시간 미리보기·편집기·저장을 시험한다 — 쓰는 법: python3 room3d_check.py <static 폴더> <그림 폴더> (playwright 필요)
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

        # ── 실시간 미리보기 (데모 값) ──
        pg.click("#liveBtn"); pg.wait_for_timeout(2600)
        라 = pg.evaluate("window.__room3d.라이브()")
        확인(라["켬"] and 라["센서"] >= 100, f"실시간 미리보기 — 가상 센서 {라['센서']}개")
        단계들 = [a[1] for a in 라["알람"]]
        확인(all(d in 단계들 for d in ("위험", "경고", "주의", "정지")), f"알람 단계 {단계들}")
        확인(any(a[0].startswith("LL-") for a in 라["알람"]) and any(a[0].startswith("AC") for a in 라["알람"]), "누수·항온항습기 알람 포함")
        확인(len(라["랙색"]) >= 3, f"랙 색 — 온도 이상 랙 {len(라['랙색'])}대")
        # ── 87차 — 설비 세부 그림 · 타공판 · 랙 흡기 온도 색 · 지난 기록 돌려보기(데모) ──
        정 = pg.evaluate("window.__room3d.재질정보('R001')")
        r1 = pg.evaluate("window.__room3d.모형().항목.find(i => i.id === 'R001')")
        이웃 = pg.evaluate("""() => { const 항 = window.__room3d.모형().항목, a = 항.find(i => i.id === 'R001');
            return 항.filter(o => o.종류 && o.종류.startsWith('rack') && o !== a && Math.hypot(o.x - a.x, o.y - a.y) < 1.3).map(o => [o.x - a.x, o.y - a.y]); }""")
        옆이웃x = any(abs(dx) > abs(dy) for dx, dy in 이웃)
        확인(정 and 정["세부"] and 정["앞x"] == (not 옆이웃x), f"랙 앞면 그림 — 이웃이 붙은 쪽은 옆면, 앞면 축 {'x' if 정 and 정['앞x'] else 'z'} (R001 {r1['w']}×{r1['d']}, 이웃 {이웃[:2]})")
        확인(pg.evaluate("window.__room3d.타공수()") >= 50, f"랙 앞 타공 바닥판 {pg.evaluate('window.__room3d.타공수()')}장")
        pg.select_option("#t_rackmode", "온도"); pg.wait_for_timeout(2300)
        라 = pg.evaluate("window.__room3d.라이브()")
        온랙 = 라["랙온도"][0][0] if 라["랙온도"] else None
        확인(len(라["랙온도"]) >= 50 and 온랙 and pg.evaluate(f"window.__room3d.재질정보('{온랙}').온도칠"), f"랙 색 「흡기 온도」 — 온도 있는 랙 {len(라['랙온도'])}대가 온도 색")
        pg.screenshot(path=f"{OUT}/03b_랙_흡기온도색.png")
        pg.click("#replayBtn"); pg.wait_for_timeout(600)
        재 = pg.evaluate("window.__room3d.라이브().재생")
        확인(재 and 재["수"] == 24 and 재["i"] == 23 and pg.is_visible("#replay"), f"⏱ 지난 기록 돌려보기 — 24시간 막대 ({재})")
        pg.locator("#replayRange").fill("5"); pg.wait_for_timeout(300)
        확인(pg.evaluate("window.__room3d.라이브().재생.i") == 5, "시간 막대를 끌면 그 시각으로")
        pg.click("#replayPlay"); pg.wait_for_timeout(1600)
        확인(pg.evaluate("window.__room3d.라이브().재생.i") >= 6, "▶ 재생 — 시각이 흘러감")
        pg.screenshot(path=f"{OUT}/03c_기록재생.png")
        pg.locator("#replay button", has_text="실시간으로").click(); pg.wait_for_timeout(300)
        확인(not pg.is_visible("#replay") and pg.evaluate("window.__room3d.라이브().재생") is None and pg.evaluate("window.__room3d.라이브().켬"), "✕ 실시간으로 — 재생 닫고 실시간 그대로")
        pg.select_option("#t_rackmode", "알람"); pg.wait_for_timeout(300)
        확인(pg.locator("#alarms .알람").count() >= 5, "알람 창 목록")
        pg.evaluate("document.querySelector('#alarms .알람').click()"); 다옴()      # 목록이 2초마다 새로 그려져 느린 시험기에서는 「안정」 을 못 기다린다
        확인("흡기 온도" in pg.inner_text("#info") or "상태" in pg.inner_text("#info"), "알람을 누르면 그 장비로 가서 실시간 값")
        pg.screenshot(path=f"{OUT}/03_실시간_알람.png")
        pg.click("#liveBtn"); pg.wait_for_timeout(300)
        확인(not pg.evaluate("window.__room3d.라이브().켬") and pg.locator("#alarms").is_hidden(), "실시간 미리보기 끄기")
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
        # 센서는 평면에서 반지름 14 px 이상으로 보이고, 가운데에서 10 px 떨어진 곳을 눌러도 골라진다
        pg.keyboard.press("Control+d")
        c = 평(항목("T01")["x"], 항목("T01")["y"])
        pg.mouse.click(c[0] + 10, c[1]); pg.wait_for_timeout(150)
        확인(고른() == ["T01"], f"센서 가장자리를 눌러도 골라짐 — {고른()}")
        pg.screenshot(path=f"{OUT}/12b_센서확대.png", clip={"x": c[0] - 60, "y": c[1] - 70, "width": 120, "height": 110})
        # 센서에는 크기 손잡이가 없고 회전 손잡이만 — 그것을 끌면 돈다
        회 = pg.evaluate("""() => { const it = window.__room3d.모형().항목.find(i => i.id === 'T01'); const 배 = window.__room3d.평면.배율;
          const r = Math.max(14, it.w * 배 / 2) / 배; const st = document.getElementById('stage').getBoundingClientRect();
          const [a, b] = window.__room3d.평면에서화면(it.x, it.y - r - 22 / 배); return [st.left + a, st.top + b]; }""")
        pg.mouse.move(*회); pg.mouse.down(); pg.mouse.move(c[0] + 60, c[1], steps=6); pg.mouse.up(); pg.wait_for_timeout(150)
        확인(abs(항목("T01")["회전"] - 90) < 1e-6 and abs(항목("T01")["w"] - 0.06) < 1e-9, f"센서 회전 손잡이 — {항목('T01')['회전']}°, 크기 그대로")

        # 작업 내역
        내역 = pg.evaluate("window.__room3d.내역()")
        확인(len(내역) > 8 and 내역[0] == "열기", f"작업 내역 {len(내역)}줄")

        # 3D 로 보기
        pg.keyboard.press("3"); 다옴(); pg.wait_for_timeout(400)
        pg.screenshot(path=f"{OUT}/13_편집_3D.png")
        # 3D 에서 센서 글자표를 끌면 센서가 옮겨진다
        pg.keyboard.press("Control+d"); pg.wait_for_timeout(100)
        t0 = 항목("T01"); s = pg.evaluate("window.__room3d.표화면('T01')")
        pg.mouse.move(s["x"], s["y"]); pg.mouse.down(); pg.mouse.move(s["x"] + 80, s["y"] + 40, steps=8); pg.mouse.up(); pg.wait_for_timeout(300)
        t1 = 항목("T01")
        확인(고른() == ["T01"] and ((t1["x"] - t0["x"]) ** 2 + (t1["y"] - t0["y"]) ** 2) ** 0.5 > 0.5,
             f"3D 에서 센서 글자표를 끌어 옮김 — ({t0['x']}, {t0['y']}) → ({t1['x']}, {t1['y']})")
        pg.keyboard.press("Control+z"); pg.wait_for_timeout(150)
        확인(항목("T01")["x"] == t0["x"], "3D 이동도 실행 취소됨")
        # 83차 「센서의 크기를 2배로」 — 점형 센서는 화면에서 두 배(바닥 면 적어도 12 cm), 배치 값은 그대로
        t = 항목("T01"); 그린 = pg.evaluate("window.__room3d.그린크기('T01')")
        확인(그린 == [max(round(t["w"] * 2, 3), .12), max(round(t["d"] * 2, 3), .12), round(t["h"] * 2, 3)] and t["w"] < .1,
             f"온도 센서 화면 크기 두 배 — 배치 {t['w']}×{t['d']}×{t['h']} m → 그림 {그린}")
        # 보기 메뉴의 「평면 (2D)」 가 옵션 막대에 가리지 않고 눌린다
        pg.click("#menus .메뉴:nth-child(3) > button"); pg.wait_for_timeout(150)
        pg.locator(".메뉴.열림 .항", has_text="평면 (2D)").click(); pg.wait_for_timeout(400)
        확인(pg.evaluate("document.getElementById('b2d').classList.contains('켬')"), "3D 에서 보기 메뉴 → 평면 (2D) 로 돌아감")
        pg.keyboard.press("2"); pg.wait_for_timeout(400)

        # 저장·다른 이름으로 저장 — 윈도우 저장 창은 시험 브라우저에서 못 누르므로, 창이 돌려주는 파일 손잡이를 흉내 낸다
        확인(not pg.evaluate("window.__room3d.저장됨()"), "고치면 「저장 안 됨」")
        pg.evaluate("""() => { window.__창 = []; window.__쓴것 = {};
          window.__다음이름 = '1층_배치.json';
          window.showSaveFilePicker = async (o) => { window.__창.push(o.suggestedName); const 이름 = window.__다음이름;
            return {name: 이름, createWritable: async () => { let 글 = ''; return {write: async (t) => { 글 += t; }, close: async () => { window.__쓴것[이름] = (window.__쓴것[이름] || []).concat([글]); }}; }}; }; }""")
        # ── 누수 감지선 마우스로 놓기 (76차) — ≋ 도구로 항온항습기 누르기 · 벽 피하기 · 길이 · 시작점 · 다른 장비로 끌기 · 일자 긋기 ──
        def 벽침범(선):
            """감지선 네 변 위 점 중 벽·기둥 속에 든 것 수 (가장자리 1 cm 는 봐준다)."""
            import math
            벽 = [w for w in pg.evaluate("window.__room3d.모형().항목") if w["종류"] in ("wall", "col")]
            c, n = math.cos(math.radians(선.get("회전") or 0)), math.sin(math.radians(선.get("회전") or 0))
            a, b, 수 = 선["w"] / 2, 선["d"] / 2, 0
            for (x0, y0, x1, y1) in [(-a, -b, a, -b), (a, -b, a, b), (a, b, -a, b), (-a, b, -a, -b)]:
                for k in range(41):
                    lx, ly = x0 + (x1 - x0) * k / 40, y0 + (y1 - y0) * k / 40
                    px, py = 선["x"] + lx * c - ly * n, 선["y"] + lx * n + ly * c
                    for w in 벽:
                        wc, wn = math.cos(math.radians(w.get("회전") or 0)), math.sin(math.radians(w.get("회전") or 0))
                        dx, dy = px - w["x"], py - w["y"]
                        if abs(dx * wc + dy * wn) < w["w"] / 2 - .01 and abs(-dx * wn + dy * wc) < w["d"] / 2 - .01:
                            수 += 1; break
            return 수
        ac8 = 항목("AC08")
        pg.keyboard.press("l"); pg.wait_for_timeout(150)
        확인("둘레 감지선 길이" in pg.inner_text("#optbar"), "≋ 도구(L) — 옵션 막대에 둘레 감지선 길이")
        pg.mouse.move(*평(ac8["x"], ac8["y"])); pg.wait_for_timeout(150)
        pg.mouse.click(*평(ac8["x"], ac8["y"])); pg.wait_for_timeout(300)
        선 = 항목(고른()[0])
        둘레 = 2 * (선["w"] + 선["d"])
        확인(선["종류"] == "s_leak_loop" and abs(둘레 - 10) < .01, f"AC08 을 누르면 둘레 감지선 {선['id']} {둘레:.2f} m")
        확인(abs(선["x"] - ac8["x"]) < .01 and 선["y"] < ac8["y"] - .3, f"AC08 뒤 벽을 피해 앞으로 밀림 (감지선 y {선['y']:.2f} · 항온항습기 y {ac8['y']:.2f})")
        확인(벽침범(선) == 0, "감지선이 벽·기둥에 안 묻힘")
        pg.screenshot(path=f"{OUT}/12c_누수선_두르기.png")
        길이칸 = pg.locator("#optbar label[data-k=감지선길이] input")
        길이칸.fill("12"); 길이칸.press("Enter"); pg.wait_for_timeout(200)
        선 = 항목(선["id"])
        확인(abs(2 * (선["w"] + 선["d"]) - 12) < .02, f"옵션 막대 길이 12 m — {2 * (선['w'] + 선['d']):.2f} m")
        w0, d0 = 선["w"], 선["d"]
        pg.locator("#optbar button", has_text="시작점").click(); pg.wait_for_timeout(200)
        선 = 항목(선["id"])
        확인(선["회전"] == 90 and abs(선["w"] - d0) < 1e-6 and abs(선["d"] - w0) < 1e-6, "↻ 시작점 — 모양 그대로 시작 모서리만 다음으로")
        ac9 = 항목("AC09")
        # 「↻ 시작점」 으로 90° 돌아 세로가 w — 위쪽 띠를 잡는다
        pg.mouse.move(*평(선["x"], 선["y"] - 선["w"] / 2 + .03)); pg.mouse.down()
        pg.mouse.move(*평(ac9["x"], ac9["y"] - .3), steps=8); pg.mouse.up(); pg.wait_for_timeout(300)
        선 = 항목(선["id"])
        확인(abs(선["x"] - ac9["x"]) < .01 and abs(2 * (선["w"] + 선["d"]) - 12) < .02 and 벽침범(선) == 0,
             f"감지선을 AC09 위로 끌어 놓으면 AC09 둘레로 다시 감김 (길이 12 m 그대로)")
        pg.mouse.move(*평(19.8, 15.8)); pg.mouse.down(); pg.mouse.move(*평(24.0, 15.8), steps=6); pg.mouse.up(); pg.wait_for_timeout(250)
        일자 = 항목(고른()[0])
        확인(일자["종류"] == "s_leak_line" and abs(일자["w"] - 4.2) < .01, f"바닥에서 끌면 일자 감지선 {일자['w']} m (바닥타일 격자)")
        ac10 = 항목("AC10")
        pg.locator("#lib .타일[data-k=s_leak_loop]").click()
        pg.mouse.click(*평(ac10["x"], ac10["y"])); pg.wait_for_timeout(300)
        선3 = 항목(고른()[0])
        확인(선3["종류"] == "s_leak_loop" and abs(선3["x"] - ac10["x"]) < .01 and abs(2 * (선3["w"] + 선3["d"]) - 10) < .01, "장비 타일 「누수 감지선 (둘레형)」 을 AC10 에 놓아도 둘레로")
        pg.keyboard.press("v"); pg.wait_for_timeout(100)
        # ── 85차 「누수감지선을 일자형과 ㄱ·ㄷ·ㄹ 모양처럼 자유롭게」 — ≋ 도구로 바닥을 차례로 누르면 꺾은선 ──
        import math
        def 월드점(it):
            c, n = math.cos(math.radians(it.get("회전") or 0)), math.sin(math.radians(it.get("회전") or 0))
            return [(round(it["x"] + lx * c - ly * n, 3), round(it["y"] + lx * n + ly * c, 3)) for lx, ly in it["점들"]]
        def 길이(it):
            q = it["점들"]; return sum(math.hypot(q[i][0] - q[i - 1][0], q[i][1] - q[i - 1][1]) for i in range(1, len(q)))
        pg.keyboard.press("l"); pg.wait_for_timeout(100)
        ㄷ = [(19.8, 17.4), (24.0, 17.4), (24.0, 19.2), (19.8, 19.2)]
        for x, y in ㄷ:
            pg.mouse.click(*평(x, y)); pg.wait_for_timeout(120)
        확인(pg.evaluate("window.__room3d.꺾는중()") == 4 and "꺾은선 그리는 중" in pg.inner_text("#optbar"), "바닥을 네 번 누름 — 꺾은선 그리는 중 점 4개")
        pg.screenshot(path=f"{OUT}/12d_꺾은선_그리는중.png")
        pg.keyboard.press("Enter"); pg.wait_for_timeout(250)
        꺾 = 항목(고른()[0])
        확인(꺾["종류"] == "s_leak_path" and 월드점(꺾) == ㄷ and abs(길이(꺾) - 10.2) < 1e-6,
             f"Enter — ㄷ자 꺾은선 감지선 {꺾['id']} {길이(꺾):.2f} m, 점 {월드점(꺾)}")
        확인(pg.evaluate(f"window.__room3d.그린크기('{꺾['id']}')") is not None, "3D 에도 꺾은선 띠")
        위 = pg.evaluate(f"window.__room3d.선위치('{꺾['id']}', 5.0)")
        확인(abs(위[0] - 24.0) < 1e-6 and abs(위[1] - 18.2) < 1e-6 and abs(위[2] - 90) < 1e-6, f"누수 위치 5.0 m — 첫 점에서 4.2 m 꺾고 0.8 m 아래 {위}")
        pg.keyboard.press("v"); pg.wait_for_timeout(100)
        pg.mouse.move(*평(19.8, 19.2)); pg.mouse.down(); pg.mouse.move(*평(18.6, 19.2), steps=6); pg.mouse.up(); pg.wait_for_timeout(250)
        꺾 = 항목(꺾["id"])
        확인(월드점(꺾)[-1] == (18.6, 19.2) and abs(길이(꺾) - 11.4) < 1e-6, f"끝 점 손잡이를 끌어 옮김 — {길이(꺾):.2f} m")
        pg.mouse.dblclick(*평(21.9, 17.4)); pg.wait_for_timeout(250)
        꺾 = 항목(꺾["id"])
        새점 = 월드점(꺾)[1] if len(꺾["점들"]) == 5 else None
        확인(새점 and abs(새점[0] - 21.9) < .05 and abs(새점[1] - 17.4) < 1e-3 and abs(길이(꺾) - 11.4) < 1e-3, f"선을 더블클릭 — 그 선 위에 점 더하기 ({len(꺾['점들'])}개 · {새점})")
        pg.mouse.move(*평(*새점)); pg.wait_for_timeout(80)
        pg.keyboard.down("Alt"); pg.mouse.click(*평(*새점)); pg.keyboard.up("Alt"); pg.wait_for_timeout(250)
        꺾 = 항목(꺾["id"])
        확인(len(꺾["점들"]) == 4, f"Alt+누르기 — 점 빼기 ({len(꺾['점들'])}개)")
        길이칸 = pg.locator("#optbar label[data-k=감지선길이] input")
        길이칸.fill("12"); 길이칸.press("Enter"); pg.wait_for_timeout(200)
        꺾 = 항목(꺾["id"])
        확인(abs(길이(꺾) - 12) < .01 and abs(월드점(꺾)[-1][1] - 19.2) < .01, f"옵션 막대 길이 12 m — 마지막 토막만 늘어남 {월드점(꺾)[-1]}")
        첫 = 월드점(꺾)[0]
        pg.locator("#optbar button", has_text="시작점").click(); pg.wait_for_timeout(200)
        확인(월드점(항목(꺾["id"]))[-1] == 첫, "⇄ 시작점 — 끝과 끝을 맞바꿈")
        pg.screenshot(path=f"{OUT}/12e_꺾은선_ㄷ자.png")
        # 그리다가 Backspace 로 한 점 지우고 Esc 로 그만두기 — 항목이 안 생김
        n = 개수()
        pg.keyboard.press("l"); pg.mouse.click(*평(19.8, 21.0)); pg.mouse.click(*평(22.2, 21.0)); pg.wait_for_timeout(100)
        pg.keyboard.press("Backspace"); 한점 = pg.evaluate("window.__room3d.꺾는중()")
        pg.keyboard.press("Escape"); pg.wait_for_timeout(100)
        확인(한점 == 1 and not pg.evaluate("window.__room3d.꺾는중()") and 개수() == n, "Backspace 한 점 지움 · Esc 그만두기 — 새 항목 없음")
        pg.keyboard.press("v"); pg.wait_for_timeout(100)

        pg.keyboard.press("Control+s"); pg.wait_for_timeout(300)
        확인(pg.evaluate("window.__창.length") == 1, "처음 Ctrl+S 는 이름이 없어 다른 이름으로 저장 창을 엶")
        확인(pg.evaluate("(window.__쓴것['1층_배치.json'] || []).length") == 1, "고른 PC 파일에 씀")
        확인(pg.evaluate("Object.keys(JSON.parse(localStorage.getItem('fms.room3d.layouts.v2')))") == ["1층_배치"], "브라우저에도 같은 이름으로 둠")
        확인("1층_배치" in pg.inner_text("#docName") and "PC 파일" in pg.inner_text("#docName"), f"제목 줄 — {pg.inner_text('#docName')}")
        n1층 = 개수()
        pg.mouse.click(*평(18.0, 8.5)); pg.keyboard.press("Delete"); pg.wait_for_timeout(150)
        확인("●" in pg.inner_text("#docName"), "고치면 제목 줄에 ●")
        pg.keyboard.press("Control+s"); pg.wait_for_timeout(300)
        확인(pg.evaluate("window.__창.length") == 1 and pg.evaluate("window.__쓴것['1층_배치.json'].length") == 2, "두 번째 Ctrl+S 는 창 없이 같은 파일에 덮어씀")
        확인(len(json.loads(pg.evaluate("window.__쓴것['1층_배치.json'][1]"))["항목"]) == n1층 - 1, "덮어쓴 파일에 지운 것이 반영됨")
        pg.evaluate("window.__다음이름 = '증설안_A.json'")
        pg.keyboard.press("Control+Shift+s"); pg.wait_for_timeout(300)
        확인(pg.evaluate("window.__창") == ["전산실_배치.json", "1층_배치.json"], f"다른 이름으로 저장 창 — 제안 이름 {pg.evaluate('window.__창')}")
        확인(sorted(pg.evaluate("Object.keys(JSON.parse(localStorage.getItem('fms.room3d.layouts.v2')))")) == ["1층_배치", "증설안_A"], "브라우저에 두 배치")
        확인(pg.evaluate("localStorage.getItem('fms.room3d.current')") == "증설안_A", "보기 화면은 새 이름의 배치를 씀")
        # 저장 창을 못 쓰는 브라우저 — 이름을 받아 내려받기
        pg.evaluate("delete window.showSaveFilePicker")
        pg.keyboard.press("Control+Shift+s"); pg.wait_for_timeout(200)
        확인(pg.locator(".대화상자 input").count() == 1, "저장 창이 없으면 이름 묻는 창")
        pg.locator(".대화상자 input").fill("야간 점검용")
        with pg.expect_download() as dl:
            pg.locator(".대화상자 button.주").click()
        확인(dl.value.suggested_filename == "야간 점검용.json", f"같은 이름으로 내려받기 — {dl.value.suggested_filename}")
        내려 = json.load(open(dl.value.path(), encoding="utf-8"))
        확인(내려["판"] == 2 and len(내려["항목"]) == 개수(), f"내려받은 JSON — {len(내려['항목'])}개")
        # 열기 창
        pg.keyboard.press("Control+o"); pg.wait_for_timeout(200)
        줄들 = pg.locator(".배치목록 .줄")
        확인(줄들.count() == 3, f"열기 창 — 브라우저 배치 {줄들.count()}개")
        pg.locator(".배치목록 .줄", has_text="1층_배치").locator("button.주").click(); pg.wait_for_timeout(300)
        확인(개수() == n1층 - 1 and "1층_배치" in pg.inner_text("#docName"), "열기 창에서 1층_배치 열기")
        pg.screenshot(path=f"{OUT}/15_편집_열기후.png")
        # 보기 화면 — 다시 열어도 지금 배치, 배치 고르기로 바꾸기
        pg.click("#toView"); pg.wait_for_timeout(500)
        pg.reload(); pg.wait_for_function("window.__room3d", timeout=20000); pg.wait_for_timeout(800)
        확인("1층_배치" in pg.inner_text("#source") and 개수() == n1층 - 1, f"다시 열면 1층_배치 — {pg.inner_text('#source')}")
        옵션 = pg.locator("#layoutSel option").all_inner_texts()
        확인(len(옵션) == 4, f"보기 화면 배치 고르기 — {옵션}")
        pg.select_option("#layoutSel", "증설안_A"); 다옴()
        확인(개수() == n1층 - 1 and "증설안_A" in pg.inner_text("#source"), "증설안_A 로 바꿔 보기")
        pg.select_option("#layoutSel", ""); 다옴()
        확인(개수() == 719 and pg.evaluate("localStorage.getItem('fms.room3d.current')") is None, f"처음 도면으로 보기 — {개수()}개")
        pg.screenshot(path=f"{OUT}/16_보기_배치고르기.png")

        # JSON 파일 열기 (파일 고르기 칸)
        pg.click("#toEdit"); pg.wait_for_timeout(800)
        내려["항목"] = 내려["항목"][:10]
        json.dump(내려, open(f"{OUT}/작은배치.json", "w", encoding="utf-8"), ensure_ascii=False)
        pg.set_input_files("#fileIn", f"{OUT}/작은배치.json"); pg.wait_for_timeout(400)
        확인(개수() == 10 and "작은배치" in pg.inner_text("#docName"), f"JSON 파일 열기 — {개수()}개, 이름 작은배치")
        pg.keyboard.press("Control+z"); pg.wait_for_timeout(200)
        확인(개수() > 600, "파일 열기도 실행 취소됨")
        pg.evaluate("localStorage.clear()")
        확인(not 오류, f"콘솔 오류·경고 {len(오류)}건 {오류[:3]}")
        b.close()
finally:
    srv.terminate()
print("실패", len(실패))
sys.exit(1 if 실패 else 0)
