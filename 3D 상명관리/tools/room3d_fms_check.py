# 관제 화면의 「3D 상면」 메뉴(FMS 연결)를 데모 서버(run_api --demo)로 띄워 크로미엄으로 시험한다 — 쓰는 법: python3 room3d_fms_check.py <그림 폴더> (playwright 필요)
#
# 71차 — 메뉴·토큰 전달·현장 배치(서울 기본 배치)·실시간 값과 알람 등급·알람의 「3D」·배치도의 「3D 로 보기」·
#        편집기 「FMS 센서」 끌어 놓기·FMS 저장·권한·현장 바꾸기·로그아웃을 차례로 본다.
import json, os, socket, subprocess, sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = sys.argv[1] if len(sys.argv) > 1 else "fms_shots"
os.makedirs(OUT, exist_ok=True)
API = Path(__file__).resolve().parents[1] / "50_api"
s = socket.socket(); s.bind(("127.0.0.1", 0)); PORT = s.getsockname()[1]; s.close()
srv = subprocess.Popen([sys.executable, "run_api.py", "--demo", "--host", "127.0.0.1", "--port", str(PORT)],
                       cwd=API, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
BASE = f"http://127.0.0.1:{PORT}"
실패 = []


def 확인(조건, 말):
    print(("통과 " if 조건 else "실패 ") + 말)
    if not 조건:
        실패.append(말)


def 기다리기(fr, 식, timeout=15000):
    """관제 화면 CSP(unsafe-eval 없음) 아래서는 wait_for_function 이 막힌다 — evaluate(CDP)로 되풀이해 본다."""
    끝 = time.time() + timeout / 1000
    while time.time() < 끝:
        try:
            if fr.evaluate(식):
                return
        except Exception:
            pass
        time.sleep(.2)
    raise TimeoutError(식)


for _ in range(60):
    try:
        socket.create_connection(("127.0.0.1", PORT), timeout=.5).close(); break
    except OSError:
        time.sleep(.5)

try:
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
        ctx = b.new_context(viewport={"width": 1700, "height": 950})
        pg = ctx.new_page()
        오류 = []
        pg.on("console", lambda m: m.type in ("error", "warning") and 오류.append(m.text))
        pg.on("pageerror", lambda e: 오류.append(str(e)))

        def 로그인(who, pw):
            pg.goto(BASE + "/")
            pg.fill("#lid", who); pg.fill("#lpw", pw); pg.press("#lpw", "Enter")
            pg.wait_for_selector("#app:not(.hide)", timeout=15000)

        def 틀():
            pg.wait_for_selector("#room3d iframe", timeout=10000)
            for _ in range(50):
                fr = next((f for f in pg.frames if "room3d.html" in f.url), None)
                if fr: break
                pg.wait_for_timeout(100)
            기다리기(fr, "window.__room3d && window.__room3d.FMS().시작됨 && window.__room3d.FMS().출처", 30000)
            return fr

        def 상태(fr):
            return fr.evaluate("window.__room3d.FMS()")

        def 다옴(fr, ms=400):
            fr.wait_for_timeout(ms); 기다리기(fr, "!window.__room3d.나는중()", 15000); fr.wait_for_timeout(300)

        # ── 1. 메뉴 — 대시보드 바로 옆 ──
        로그인("admin", "admin")
        메뉴 = pg.eval_on_selector_all("#menu button", "bs => bs.map(b => b.textContent)")
        확인(메뉴[:2] == ["대시보드", "3D 상면"], f"위 메뉴 순서 — {메뉴}")
        pg.click('#menu button[data-mode="room3d"]')
        fr = 틀()
        기다리기(fr, "window.__room3d.FMS().점 > 0", 15000)
        st = 상태(fr)
        확인(st["켬"] and st["현장"] == "SEOUL", f"FMS 연결·서울센터 — {st['현장']}")
        확인(st["출처"] == "기본", f"서버에 배치가 없어 기본 배치(room3d_site_SEOUL.json) — {st['출처']}")
        확인(st["점"] >= 170, f"서울센터 센서 목록 — {st['점']}개")
        확인("token" not in fr.url and "Bearer" not in fr.url, f"iframe 주소에 토큰 없음 — {fr.url.replace(BASE, '')}")
        기다리기(fr, "Object.keys(window.__room3d.FMS().값).length > 50", 15000)
        st = 상태(fr); 값 = st["값"]
        코드수 = fr.evaluate("window.__room3d.모형().항목.filter(it => it.점).length")
        확인(len(값) == 코드수, f"코드 붙은 항목마다 값 — {len(값)} / {코드수}")
        없음 = [k for k, v in 값.items() if any("없음" in g and "코드" in g for g in v["글"])]
        확인(not 없음, f"코드 없음 0건 — {없음[:5]}")
        print("   값 보기:", {k: 값[k] for k in ("AC05", "AC07", "R01-03", "LL05", "UPS01", "TH01", "T03", "WS02") if k in 값})
        확인(값["LL05"]["단계"] == "위험" and "누수 감지" in 값["LL05"]["글"][0], f"5열 누수(PLAN.LEAK.05 위급 알람) — {값['LL05']}")
        확인(값["UPS01"]["단계"] == "위험", f"UPS 배터리 전압 저하(중대) → UPS 위험 — {값['UPS01']}")
        확인(값["AC05"]["단계"] == "위험" and "경보" in 값["AC05"]["글"][0], f"CRAC-05 펌프 정지(중대) → 항온항습기 경보 — {값['AC05']}")
        확인(값["TH01"]["단계"] == "주의", f"3층 실내 온도 상승(주의) → 온습도 주의 — {값['TH01']}")
        확인("℃" in 값["R01-03"]["글"][0], f"랙에 붙은 흡입온도 — {값['R01-03']}")
        확인(st["밖알람"] >= 1, f"배치 안 된 센서의 알람도 센다 — {st['밖알람']}건")
        # 87차 — 알람 말풍선 개수(Siemens 방식): 센서가 여럿 붙은 항온항습기 표에 「⚠ 위험 1 / 센서 4」
        표 = fr.evaluate("window.__room3d.표글('AC05')") or []
        확인(any(x.startswith("⚠ 위험") and "센서" in x for x in 표), f"AC05 표에 알람 개수 줄 — {표}")
        # 87차 — ⏱ 지난 기록 돌려보기: 온도 점의 1시간 평균을 받아 시각을 돌린다
        fr.evaluate("window.__room3d.재생열기(168)")
        기다리기(fr, "(r => r && window.document.getElementById('replayNote').textContent.includes('온도 센서'))(window.__room3d.라이브().재생)", 30000)
        재 = fr.evaluate("window.__room3d.라이브().재생"); 노트 = fr.inner_text("#replayNote")
        확인(재["수"] == 168 and "못 받음" not in 노트 and "기록 재생" in fr.inner_text("#alarms"), f"FMS 기록 재생 7일 — {노트}")
        기록있는 = fr.evaluate("""() => { const r = window.__room3d; for (let i = 0; i < 168; i++) { r.재생보기(i);
            const v = Object.values(r.FMS().값).filter(x => x.글 && /℃$/.test(x.글[0] || '') ); if (v.length) return [i, v.length]; } return null; }""")
        확인(기록있는 is not None, f"기록 시각에는 온도 센서가 그 시각 값 — {기록있는}")
        pg.screenshot(path=f"{OUT}/02b_서울_기록재생.png")
        fr.locator("#replay button", has_text="실시간으로").click(); fr.wait_for_timeout(600)
        확인(fr.evaluate("window.__room3d.라이브().재생") is None and "FMS 실시간" in fr.inner_text("#alarms"), "실시간으로 돌아옴")
        알람글 = fr.inner_text("#alarms")
        확인("FMS 실시간" in 알람글 and "데모" not in 알람글, "알람 창 머리 — FMS 실시간")
        pg.wait_for_timeout(800)
        pg.screenshot(path=f"{OUT}/01_서울_전체.png")

        # ── 2. 알람 창에서 누르면 그 자리로 ──
        fr.click("#alarms .알람 >> nth=0"); 다옴(fr, 900)
        pg.screenshot(path=f"{OUT}/02_서울_첫알람.png")
        fr.evaluate("window.__room3d.알람으로('AC05')"); 다옴(fr, 900)
        pg.screenshot(path=f"{OUT}/03_서울_CRAC05.png")
        fr.evaluate("window.__room3d.고른().length")
        fr.evaluate("window.__room3d.알람으로('R01-03')"); 다옴(fr, 900)
        정보 = fr.inner_text("#info")
        확인("RACK.R1C1.TEMP" in 정보 and "흡입온도" in 정보, f"랙 정보 창에 FMS 센서 값 — {정보[:80]!r}")
        pg.screenshot(path=f"{OUT}/04_서울_랙열.png")
        fr.evaluate("window.__room3d.알람으로('LL05')"); 다옴(fr, 900)
        pg.screenshot(path=f"{OUT}/05_서울_5열누수.png")

        # ── 3. 관제 화면 알람의 「3D」 → 그 센서 자리 ──
        pg.click('#menu button[data-mode="dash"]'); pg.wait_for_timeout(1500)
        단추 = pg.locator("#alarms .alarm .btns button", has_text="3D")
        확인(단추.count() >= 5, f"알람마다 「3D」 단추 — {단추.count()}개")
        누수알람 = pg.locator("#alarms .alarm", has_text="5열 누수 감지")
        누수알람.locator("button", has_text="3D").click()
        기다리기(fr, "window.__room3d.고른().length === 0 || true"); 다옴(fr, 1200)
        확인(pg.eval_on_selector("#room3d", "e => !e.classList.contains('hide')"), "「3D」 를 누르면 3D 상면 메뉴로")
        pg.screenshot(path=f"{OUT}/06_알람에서_3D.png")
        pid = pg.evaluate("S.alarms.filter(a => /누수 12/.test(a.message))[0].point_id")
        pg.evaluate(f"openRoom3d(1, {pid})"); fr.wait_for_timeout(900)
        확인("3D 배치에 없습니다" in fr.inner_text("#info") and "LEAK.12" in fr.inner_text("#info"), "배치 안 된 센서의 「3D」 — 끌어 놓으라고 알림")

        # ── 4. 배치도(2D)의 「3D 로 보기」 ──
        pg.click('#menu button[data-mode="dash"]'); pg.wait_for_timeout(800)
        pg.evaluate("openDashboard(S.dashboards.filter(d => d.code === 'FLOOR3')[0].id)")
        pg.wait_for_timeout(2000)
        확인(pg.locator(".plan .go3d").count() == 1, "2D 배치도는 그대로, 「3D 로 보기」 단추")
        pg.screenshot(path=f"{OUT}/07_2D배치도_3D단추.png")
        pg.click(".plan .go3d"); pg.wait_for_timeout(800)
        확인(pg.eval_on_selector("#room3d", "e => !e.classList.contains('hide')"), "「3D 로 보기」 → 3D 상면")

        # ── 5. 편집기 「FMS 센서」 판 — 누르고 자리 누르기, 끌어 놓기, FMS 에 저장 ──
        fr.click("#toEdit"); fr.wait_for_timeout(900)
        확인(fr.is_visible("#p_fms"), "편집기에 FMS 센서 판")
        목록 = fr.inner_text("#fmsList")
        확인("LEAK.12" in 목록 and "PLAN.TEMP.03" not in 목록, "안 놓은 것만 — LEAK.12 있음, 놓은 PLAN.TEMP.03 없음")
        fr.fill("#fmsList input[placeholder]", "LEAK.12"); fr.wait_for_timeout(300)
        fr.click("#fmsList .층목록 div >> nth=0")
        box = pg.locator("#room3d iframe").bounding_box()
        x, y = fr.evaluate("window.__room3d.평면에서화면(13.0, 9.9)")
        sr = fr.evaluate("(() => { const r = document.getElementById('stage').getBoundingClientRect(); return [r.left, r.top]; })()")
        pg.mouse.click(box["x"] + sr[0] + x, box["y"] + sr[1] + y); fr.wait_for_timeout(400)
        새것 = fr.evaluate("window.__room3d.모형().항목.filter(it => it.점 === 'LEAK.12').map(it => [it.id, it.종류, it.이름])")
        확인(len(새것) == 1 and 새것[0][1] == "s_leak", f"누르고 놓기 — 코드·종류·이름이 붙음 {새것}")
        # 끌어 놓기 — 항온항습기가 아닌 UPS 장치 묶음이 아니라 풍속 센서 하나
        fr.fill("#fmsList input[placeholder]", "WIND.03"); fr.wait_for_timeout(300)
        x2, y2 = fr.evaluate("window.__room3d.평면에서화면(19.4, 10.6)")
        fr.evaluate("""([sx, sy]) => { const 줄 = document.querySelector('#fmsList .층목록 div'); const dt = new DataTransfer();
            줄.dispatchEvent(new DragEvent('dragstart', {dataTransfer: dt, bubbles: true}));
            const r = document.getElementById('stage').getBoundingClientRect();
            const o = {dataTransfer: dt, bubbles: true, cancelable: true, clientX: r.left + sx, clientY: r.top + sy};
            document.getElementById('stage').dispatchEvent(new DragEvent('dragover', o));
            document.getElementById('stage').dispatchEvent(new DragEvent('drop', o)); }""", [x2, y2])
        fr.wait_for_timeout(400)
        끈것 = fr.evaluate("window.__room3d.모형().항목.filter(it => it.점 === 'WIND.03').map(it => [it.id, it.종류, it.이름])")
        확인(len(끈것) == 1 and 끈것[0][1] == "s_wind", f"끌어 놓기 — {끈것}")
        pg.screenshot(path=f"{OUT}/08_편집_FMS센서판.png")
        fr.press("body", "Control+s"); fr.wait_for_timeout(900)
        확인("FMS 에 저장했습니다" in fr.inner_text("#status"), "Ctrl+S → FMS 에 저장")
        tok = pg.evaluate("TOKEN")
        저장본 = pg.evaluate("t => fetch('/api/sites/1/room-layout', {headers: {Authorization: 'Bearer ' + t}}).then(r => r.json())", tok)
        확인(저장본["layout"] and any(it.get("점") == "LEAK.12" for it in 저장본["layout"]["항목"]) and 저장본["saved_by"] == "admin",
             f"서버에 저장된 서울 배치 — {len(저장본['layout']['항목'])}개, {저장본['saved_by']}")
        fr.click("#toView"); fr.wait_for_timeout(1200)
        확인(상태(fr)["출처"] == "서버" and 상태(fr)["값"].get(새것[0][0]), "보기로 돌아오면 실시간 값 다시 켜짐 · 새 센서도 값")

        # ── 6. 현장 바꾸기 — 부산은 서버 배치가 없어 부산 기본 배치, 센서 4개가 UPS·온습도에 붙는다 (79차) ──
        fr.select_option("#layoutSel", "2"); 기다리기(fr, "window.__room3d.FMS().현장 === 'BUSAN' && window.__room3d.FMS().출처", 15000)
        확인(상태(fr)["출처"] == "기본", f"부산센터 — 서버 배치 없음 → 기본 배치(room3d_site_BUSAN.json) ({상태(fr)['출처']})")
        기다리기(fr, "(v => v.UPS01 && v.TH01)(window.__room3d.FMS().값)", 15000); 다옴(fr, 2500)
        값 = 상태(fr)["값"]
        보임 = sorted(fr.evaluate("window.__room3d.표보임()"))
        확인(보임 == ["TH01", "UPS01"] and "코드를 못 찾은" not in fr.inner_text("#alarms"),
             f"부산 값 — UPS {값['UPS01']['글']} · 온습도 {값['TH01']['글']} (표 {보임})")
        # 79차 「서울센터 제외하고 값들이 너무 복잡 — 정상값은 작게, 장애는 지금처럼」 — 작은 방·센서 몇 개여도 정상 값은 칩
        fr.evaluate("window.__room3d.시점들.iso()"); 다옴(fr, 2500)
        칩 = sorted(fr.evaluate("window.__room3d.표칩()"))
        확인(칩 == ["TH01", "UPS01"], f"부산 전체 보기 — 정상 값 2개 모두 작은 칩 ({칩})")
        pg.screenshot(path=f"{OUT}/08b_부산_정상값_칩.png")
        fr.evaluate("window.__room3d.덮어쓰기({UPS01: {단계: '위험', 글: ['배터리 전압 41.0 V', '부하율 55.0 %']}})")
        fr.wait_for_timeout(5600); 다옴(fr, 800)
        칩 = sorted(fr.evaluate("window.__room3d.표칩()")); 보임 = sorted(fr.evaluate("window.__room3d.표보임()"))
        확인(칩 == ["TH01"] and "UPS01" in 보임, f"UPS 위험 → 큰 표, 정상 온습도는 칩 그대로 (칩 {칩} · 보임 {보임})")
        pg.screenshot(path=f"{OUT}/08c_부산_UPS위험_큰표.png")
        fr.evaluate("window.__room3d.덮어쓰기({})"); fr.wait_for_timeout(5600)
        fr.select_option("#layoutSel", "1"); 기다리기(fr, "window.__room3d.FMS().현장 === 'SEOUL' && window.__room3d.FMS().출처 === '서버'", 15000)
        확인(True, "서울로 돌아오면 저장한 배치")
        # 서울 전체 보기 — 값 표가 많아도(78) 멀리서 정상 값이 작게라도 보인다 (73차)
        fr.evaluate("window.__room3d.시점들.iso()"); 다옴(fr, 2500)
        보임 = fr.evaluate("window.__room3d.표보임()")
        모두 = fr.evaluate("window.__room3d.표수()")
        이상 = [k for k, v in 상태(fr)["값"].items() if v["단계"] != "정상"]
        크게본것 = fr.evaluate("(ids => ids.filter(id => { const v = window.__room3d.FMS().값[id]; return v && v.단계 !== '정상'; }))(window.__room3d.표보임())")
        확인(all(k in 보임 for k in 이상) and len(보임) >= 12,
             f"서울 전체 보기 — 이상 값 {len(이상)}개 전부 크게 + 정상 값은 작은 칩 (표 {len(보임)} / {모두}개 보임, 77차)")
        pg.screenshot(path=f"{OUT}/09_서울_전체_값표.png")

        # ── 6-1. 센서 몇 개만 놓은 현장 — 전체 보기(멀리)에서도 정상 값이 보여야 한다 (73차 사용자 「센서 값이 보이지 않는다」) ──
        대전 = fr.evaluate("""() => { const m = JSON.parse(JSON.stringify(window.__room3d.모형()));
            m.항목 = m.항목.filter(it => it.종류 !== 'rack' && !it.점);
            m.항목.push({id: 'UPS01', 종류: 'ups', 이름: 'UPS', x: 22, y: 9, w: 1.2, d: .8, h: 1.95, z0: 0, 회전: 0, 점: 'DJ.UPS01'},
                        {id: 'T01', 종류: 's_temp', 이름: '온도 센서', x: 25, y: 9, w: .06, d: .03, h: .1, z0: 1.5, 회전: 0, 점: 'DJ.ENV.TEMP'},
                        {id: 'H01', 종류: 's_humi', 이름: '습도 센서', x: 26, y: 9, w: .06, d: .03, h: .1, z0: 1.5, 회전: 0, 점: 'DJ.ENV.HUMI'},
                        {id: 'X01', 종류: 's_temp', 이름: '없는 코드', x: 27, y: 9, w: .06, d: .03, h: .1, z0: 1.5, 회전: 0, 점: 'NO.SUCH.TEMP'});
            return {판: 2, 방: m.방, 항목: m.항목}; }""")
        r = pg.evaluate("([t, m]) => fetch('/api/sites/3/room-layout', {method: 'PUT', headers: {Authorization: 'Bearer ' + t, 'Content-Type': 'application/json'}, body: JSON.stringify({layout: m})}).then(r => r.status)", [tok, 대전])
        확인(r == 200, f"대전 배치 저장 — {r}")
        fr.select_option("#layoutSel", "3"); 기다리기(fr, "window.__room3d.FMS().현장 === 'DAEJEON' && window.__room3d.FMS().출처 === '서버'", 15000)
        기다리기(fr, "Object.keys(window.__room3d.FMS().값).length === 4", 15000); 다옴(fr, 2500)
        거리 = fr.evaluate("window.__room3d.camera.position.distanceTo(window.__room3d.controls.target)")
        보임 = sorted(fr.evaluate("window.__room3d.표보임()"))
        확인(보임 == ["H01", "T01", "UPS01"], f"대전 전체 보기(거리 {거리:.0f} m) — 정상 값 표 {보임} (코드를 못 찾은 X01 은 표 없음)")
        알람글 = fr.inner_text("#alarms")
        확인("코드를 못 찾은 항목 1개" in 알람글 and "NO.SUCH" not in 알람글, "코드 못 찾은 항목은 알람 목록이 아니라 개수로만 (77차)")
        pg.screenshot(path=f"{OUT}/10_대전_센서3개_전체.png")

        # ── 6-2. 대전 항온항습기·10 m 거리감지 누수·랙 2대 — 현장 설정 스크립트(90_ops/site_setup/daejeon_crac.js) 두 번 (75차) ──
        js = (Path(__file__).resolve().parents[1] / "90_ops" / "site_setup" / "daejeon_crac.js").read_text(encoding="utf-8")
        for n in (1, 2):
            앞 = len(오류)
            pg.evaluate(js); 기다리기(pg.main_frame, "window.__daejeon && window.__daejeon.done", 30000)
            # 데모 서버(메모리 저장소)는 DB 조회(/api/db/query)가 403 — 스크립트가 알람 룰 단계만 건너뛴다. 그 줄은 뺀다
            오류[앞:] = [x for x in 오류[앞:] if "403" not in x]
            결과 = pg.evaluate("window.__daejeon")
            확인(not 결과["errors"], f"daejeon_crac.js {n}번째 — {결과['log'][-1] if 결과['log'] else ''} {결과['errors']}")
        배치 = pg.evaluate("t => fetch('/api/sites/3/room-layout', {headers: {Authorization: 'Bearer ' + t}}).then(r => r.json())", tok)["layout"]
        항 = 배치["항목"]
        크랙 = [x for x in 항 if x.get("점") == "DJ.CRAC01"]; 둘레 = [x for x in 항 if x.get("점") == "DJ.LEAK01"]
        랙 = [x for x in 항 if x["종류"] == "rack" and x.get("이름", "").startswith("대전 랙")]
        확인(len(크랙) == 1 and len(둘레) == 1 and 둘레[0]["종류"] == "s_leak_loop" and abs(2 * (둘레[0]["w"] + 둘레[0]["d"]) - 10) < .01
             and abs(둘레[0]["x"] - 크랙[0]["x"]) < .5 and abs(둘레[0]["y"] - 크랙[0]["y"]) < .5,     # 벽을 피해 조금 밀릴 수 있다 (76차)
             f"항온항습기 {크랙[0]['id'] if 크랙 else '-'} 둘레에 10 m 누수 감지선 하나 (두 번 돌려도)")
        확인(len(랙) == 2, f"랙 2대 (두 번 돌려도 2대) — {[x['id'] for x in 랙]}")
        # 76차 — 감지선이 벽 속에 묻히지 않고, 랙은 벽 너머가 아니라 항온항습기 앞 열린 쪽에
        import math
        벽 = [w for w in 항 if w["종류"] in ("wall", "col")]
        def 벽속(px, py, 덜=.01):
            for w in 벽:
                c, n = math.cos(math.radians(w.get("회전") or 0)), math.sin(math.radians(w.get("회전") or 0))
                dx, dy = px - w["x"], py - w["y"]
                if abs(dx * c + dy * n) < w["w"] / 2 - 덜 and abs(-dx * n + dy * c) < w["d"] / 2 - 덜:
                    return True
            return False
        L = 둘레[0]; ha, hb = L["w"] / 2, L["d"] / 2
        테두리 = [(L["x"] + x0 + (x1 - x0) * k / 40, L["y"] + y0 + (y1 - y0) * k / 40)
                for (x0, y0, x1, y1) in [(-ha, -hb, ha, -hb), (ha, -hb, ha, hb), (ha, hb, -ha, hb), (-ha, hb, -ha, -hb)] for k in range(41)]
        확인(not any(벽속(x, y) for x, y in 테두리), f"둘레 감지선이 벽·기둥 속에 안 묻힘 ({L['x']:.2f}, {L['y']:.2f})")
        C = 크랙[0]
        사이벽 = [r["id"] for r in 랙 if any(벽속(C["x"] + (r["x"] - C["x"]) * k / 30, C["y"] + (r["y"] - C["y"]) * k / 30) for k in range(1, 30))]
        확인(not 사이벽 and not any(벽속(r["x"], r["y"]) for r in 랙), f"랙이 항온항습기와 같은 쪽 (사이에 벽 없음) {사이벽}")
        fr.select_option("#layoutSel", "1"); 기다리기(fr, "window.__room3d.FMS().현장 === 'SEOUL'", 15000)
        fr.select_option("#layoutSel", "3"); 기다리기(fr, "window.__room3d.FMS().현장 === 'DAEJEON' && window.__room3d.FMS().출처 === '서버'", 15000)
        기다리기(fr, f"(v => v['{크랙[0]['id']}'] && v['{둘레[0]['id']}'])(window.__room3d.FMS().값)", 15000)    # 서울 → 대전을 바로 바꿔도 대전 배치 (늦은 서울 응답이 덮지 않는다)
        값 = 상태(fr)["값"]
        확인("환기 24" in " ".join(값[크랙[0]["id"]]["글"]) or "환기" in " ".join(값[크랙[0]["id"]]["글"]), f"항온항습기 값 — {값[크랙[0]['id']]}")
        확인(값[둘레[0]["id"]]["글"][0] == "누수 없음", f"둘레 감지선 — {값[둘레[0]['id']]}")
        fr.evaluate(f"window.__room3d.알람으로('{크랙[0]['id']}')"); 다옴(fr, 1500)
        pg.screenshot(path=f"{OUT}/11_대전_항온항습기_둘레누수_평소.png")
        fr.evaluate(f"window.__room3d.덮어쓰기({{'{둘레[0]['id']}': {{누수: true, 거리: 6.2, 위치: 6.2, 단계: '위험', 글: ['누수 감지 · 6.2 m 지점']}}}})")
        fr.wait_for_timeout(5600); 다옴(fr, 600)
        확인(상태(fr)["값"][둘레[0]["id"]]["단계"] == "위험", "누수 6.2 m 지점 — 위험")
        pg.screenshot(path=f"{OUT}/12_대전_둘레누수_6m.png")
        fr.evaluate("window.__room3d.덮어쓰기({})")
        fr.select_option("#layoutSel", "1"); 기다리기(fr, "window.__room3d.FMS().현장 === 'SEOUL' && window.__room3d.FMS().출처 === '서버'", 15000)

        # ── 7. 로그아웃하면 iframe(토큰)을 버린다 · 보기 권한만 있으면 저장 안 됨 ──
        pg.click("#logoutBtn"); pg.wait_for_timeout(500)
        확인(pg.locator("#room3d iframe").count() == 0, "로그아웃 → 3D iframe 제거")
        로그인("viewer", "viewer")
        pg.click('#menu button[data-mode="room3d"]')
        fr = 틀()
        확인(상태(fr)["출처"] == "서버", "다른 사람(viewer)도 같은 서울 배치")
        fr.click("#toEdit"); fr.wait_for_timeout(600)
        fr.press("body", "Control+s"); fr.wait_for_timeout(500)
        확인("권한(topo.edit)이 없습니다" in fr.inner_text("#status"), "viewer 는 FMS 저장 안 됨 — 알림")
        fr.click("#toView"); fr.wait_for_timeout(500)

        확인(not 오류, f"콘솔 오류·경고 0건 {오류[:4]}")
        b.close()
finally:
    srv.terminate()
print("실패", len(실패))
sys.exit(1 if 실패 else 0)
