# 단독 데모(demo.html)를 파일로 열어 「3D 상면」 이 서버판처럼 FMS 연결로 도는지 크로미엄으로 본다 — 쓰는 법: python3 room3d_demo_check.py <그림 폴더> [demo.html] [http] (playwright 필요)
#   세 번째에 http 를 주면 파일 대신 http://127.0.0.1 로 연다 — GitHub Pages 처럼 출처가 있는 주소 (121차, 파일로 열 때만 되던 연결)
#
# 90차 (2026-10-14, 사용자 「지금까지 했는 내용을 demo.html 에 적용. 앞으로 계속 적용해라」)
#   현장 고르기(서울·부산·대전) · 센터 기본 배치 · 데모 센서 값과 알람 · 현장 바꾸기 · 알람의 「3D」 로 그 센서 앞으로 ·
#   배치 저장(이 창 안에서만) · 콘솔 오류 0 을 차례로 본다.
import os, sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = sys.argv[1] if len(sys.argv) > 1 else "demo_shots"
DEMO = Path(sys.argv[2] if len(sys.argv) > 2 else Path(__file__).resolve().parent / "demo.html").resolve()
HTTP = len(sys.argv) > 3 and sys.argv[3] == "http"
os.makedirs(OUT, exist_ok=True)
실패 = []


def 확인(조건, 말):
    print(("통과 " if 조건 else "실패 ") + 말)
    if not 조건:
        실패.append(말)


def 기다리기(fr, 식, timeout=60000):
    끝 = time.time() + timeout / 1000
    while time.time() < 끝:
        try:
            if fr.evaluate(식):
                return True
        except Exception:
            pass
        time.sleep(.3)
    return False


with sync_playwright() as p:
    b = p.chromium.launch(args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
    pg = b.new_page(viewport={"width": 1600, "height": 900}); pg.set_default_timeout(90000)
    오류 = []
    pg.on("console", lambda m: m.type in ("error", "warning") and 오류.append(m.text))
    pg.on("pageerror", lambda e: 오류.append(str(e)))
    if HTTP:
        import functools, http.server, threading
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(
            type("조용", (http.server.SimpleHTTPRequestHandler,), {"log_message": lambda *a: None}), directory=str(DEMO.parent)))
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        pg.goto(f"http://127.0.0.1:{srv.server_address[1]}/{DEMO.name}")
    else:
        pg.goto(DEMO.as_uri())
    pg.wait_for_timeout(2500)

    # 96차 — 3D 를 한 번도 안 연 채 장애 내역 팝업의 센서를 눌러도 그 센서까지 시선이 간다.
    # 전에는 3D 화면이 처음 뜨면서 현장을 읽는 동안 「그 센서로 가기」 가 먼저 와서 버려졌다 — 3D 화면만 뜨고 끝
    pg.evaluate("showKpiDetail('sensor', '이상이 있는 센서')")
    pg.wait_for_selector("#modal td.go3d", timeout=10000)
    pg.locator("#modal td.go3d", has_text="CRAC-05 펌프1").first.click()
    fr0 = None
    for _ in range(100):
        fr0 = next((f for f in pg.frames if f != pg.main_frame and f.url == "about:srcdoc"), None)
        if fr0: break
        time.sleep(.2)
    처음 = fr0 is not None and 기다리기(fr0, """window.__room3d && window.__room3d.FMS().현장 === 'SEOUL' && !window.__room3d.나는중()
      && window.__room3d.고른().some(id => (window.__room3d.모형().항목.find(i => i.id === id) || {}).점 === 'CRAC-05')
      && (() => { const R = window.__room3d, it = R.모형().항목.find(i => i.점 === 'CRAC-05'), t = R.controls.target;
                  return Math.hypot(t.x - it.x, t.z - it.y) < 1.5 && R.camera.position.distanceTo(t) < 15; })()""")
    확인(처음, f"3D 를 처음 열면서 센서 칸 → 그 센서까지 시선 ({fr0.evaluate('window.__room3d.고른()') if fr0 else None})")
    pg.screenshot(path=f"{OUT}/d0_처음_센서로.png")
    pg.evaluate("setMode('dash')"); pg.wait_for_timeout(500)
    pg.click('#menu button[data-mode="room3d"]')
    fr = None
    for _ in range(100):
        fr = next((f for f in pg.frames if f != pg.main_frame and f.url == "about:srcdoc"), None)
        if fr: break
        time.sleep(.2)
    확인(fr is not None, "3D 상면 메뉴 — 3D 화면이 뜸")
    서울 = 기다리기(fr, "window.__room3d && window.__room3d.FMS().현장 === 'SEOUL' && window.__room3d.라이브().켬 && window.__room3d.라이브().알람.length > 0")
    f0 = fr.evaluate("window.__room3d.FMS()")
    현장들 = fr.evaluate("[...document.getElementById('layoutSel').options].map(o => o.textContent)")
    확인(서울 and f0["출처"] == "기본" and f0["점"] > 0, f"서울센터 기본 배치 · FMS 센서 {f0['점']}개 · 알람 {fr.evaluate('window.__room3d.라이브().알람.length')}건")
    확인(len(현장들) >= 3 and "부산센터" in 현장들, f"현장 고르기 {현장들}")
    pg.screenshot(path=f"{OUT}/d1_데모_서울.png")

    부산 = next(o for o in fr.evaluate("[...document.getElementById('layoutSel').options].map(o => [o.value, o.textContent])") if o[1] == "부산센터")
    fr.select_option("#layoutSel", 부산[0])
    확인(기다리기(fr, "window.__room3d.FMS().현장 === 'BUSAN' && window.__room3d.FMS().출처 === '기본' && window.__room3d.라이브().켬"),
         f"부산센터로 바꾸기 — 기본 배치 ({fr.evaluate('window.__room3d.FMS().출처')})")
    pg.screenshot(path=f"{OUT}/d2_데모_부산.png")

    # 알람의 「3D」 — 관제 화면(부모)이 openRoom3d(현장, 센서) 를 부르면 서울로 돌아와 그 장비를 고른다
    표 = pg.evaluate("fetch('/api/points').then(r => r.json()).then(b => b.points.filter(p => p.site_id === 1).map(p => [p.id, p.tag]))")
    fr.select_option("#layoutSel", next(o[0] for o in fr.evaluate("[...document.getElementById('layoutSel').options].map(o => [o.value, o.textContent])") if o[1] == "서울센터"))
    기다리기(fr, "window.__room3d.FMS().현장 === 'SEOUL' && window.__room3d.라이브().켬")
    코드들 = fr.evaluate("window.__room3d.모형().항목.filter(i => i.점).map(i => [i.id, i.점])")
    짝 = next(((pid, iid) for pid, tag in 표 for iid, c in 코드들 if tag == c or tag.startswith(c + ".")), None)
    fr.select_option("#layoutSel", 부산[0]); 기다리기(fr, "window.__room3d.FMS().현장 === 'BUSAN'")
    확인(짝 is not None, f"서울 배치에 붙은 FMS 센서 찾기 ({짝})")
    if 짝:
        pg.evaluate(f"openRoom3d(1, {짝[0]})")
        확인(기다리기(fr, f"window.__room3d.FMS().현장 === 'SEOUL' && window.__room3d.고른().includes('{짝[1]}')"),
             f"알람의 「3D」 — 서울로 돌아와 {짝[1]} 고름 ({fr.evaluate('window.__room3d.고른()')})")
        pg.wait_for_timeout(1500); pg.screenshot(path=f"{OUT}/d3_데모_3D로가기.png")

    # 119차 — 데모 센서는 서울·대전·부산 기본 배치에 다 놓였다. 장애가 난 센서(활성 알람)마다 3D 가 그 자리를 고르는지
    없는들 = [tag for pid, tag in 표 if not any(tag == c or tag.startswith(c + ".") for _, c in 코드들)]
    확인(not 없는들, f"서울 데모 센서가 모두 3D 배치에 있음 (빠짐 {없는들[:5]})")
    알람들 = pg.evaluate("fetch('/api/alarms').then(r => r.json()).then(b => (b.alarms || b).filter(a => a.point_id).map(a => [a.site_id, a.point_id]))")
    태그 = dict(표)
    for sid, pid in 알람들:
        if sid != 1 or pid not in 태그:
            continue
        항목 = next((iid for iid, c in 코드들 if 태그[pid] == c or 태그[pid].startswith(c + ".")), None)
        pg.evaluate(f"openRoom3d(1, {pid})")
        # 장비는 골라 지고, 센서(온도·누수 등)는 고르지 않고 시선이 그 자리로 날아간다 (알람으로 — 84차 설계)
        식 = (f"(() => {{ const R = window.__room3d, it = R.모형().항목.find(i => i.id === '{항목}'); if (!it || R.FMS().현장 !== 'SEOUL' "
              f"|| R.나는중() || document.querySelector('.대화막')) return false; if (R.고른().includes(it.id)) return true; "
              f"const t = R.controls.target; return Math.abs(t.x - it.x) < Math.max(1, it.w) && Math.abs(t.z - it.y) < Math.max(1, it.w, it.d); }})()")
        확인(항목 is not None and 기다리기(fr, 식, 30000),
             f"장애 센서 {태그[pid]} → 3D 그 자리 ({항목}, 고름 {fr.evaluate('window.__room3d.고른()')}, "
             f"시선 {fr.evaluate('[window.__room3d.controls.target.x.toFixed(1), window.__room3d.controls.target.z.toFixed(1)]')})")
    pg.screenshot(path=f"{OUT}/d3c_장애센서_3D.png")

    # 97차 — 3D 배치에 붙지 않은 센서로 가라고 하면 팝업창으로 알린다 (전에는 왼쪽 아래 정보 칸에 글만 바뀌었다)
    #   119차부터 데모 센서는 모두 배치에 있다 — 배치 편집에서 한 항목의 센서 연결을 풀어 「붙지 않은 센서」 를 만든다
    없는 = next((pid for pid, tag in 표 if tag == "LEAK.12"), None)
    if 없는:
        fr.evaluate("window.__room3d.모형().항목.filter(i => i.점 === 'LEAK.12').forEach(i => { delete i.점; })")
    if 없는:
        pg.evaluate(f"openRoom3d(1, {없는})")
        뜸 = 기다리기(fr, "!!document.querySelector('.대화막') && document.querySelector('.대화막').textContent.includes('3D 배치에 없습니다')", 30000)
        글 = fr.evaluate("(document.querySelector('.대화막') || {}).textContent || ''")
        확인(뜸 and "배치 편집" in 글, f"배치에 없는 센서 → 팝업창 ({글[:60]})")
        pg.screenshot(path=f"{OUT}/d3b_배치에없는센서.png")
        if 뜸:
            fr.evaluate("[...document.querySelectorAll('.대화막 button')].find(b => b.textContent === '닫기').click()")
            확인(fr.evaluate("!document.querySelector('.대화막')"), "팝업창 「닫기」")

    # 93차 — 장애 내역 팝업의 센서 칸을 누르면 3D 상면의 그 센서로 (「CRAC-05 펌프1」 = 서울 배치 CRAC-05)
    fr.select_option("#layoutSel", 부산[0]); 기다리기(fr, "window.__room3d.FMS().현장 === 'BUSAN'")
    pg.evaluate("setMode('dash')"); pg.wait_for_timeout(500)
    pg.evaluate("showKpiDetail('sensor', '이상이 있는 센서')")
    pg.wait_for_selector("#modal td.go3d", timeout=10000)
    칸 = pg.locator("#modal td.go3d", has_text="CRAC-05 펌프1").first
    확인(칸.count() == 1, "장애 내역 팝업 — 센서 칸이 누를 수 있음")
    pg.screenshot(path=f"{OUT}/d4_장애내역_센서칸.png")
    칸.click()
    확인(기다리기(fr, """window.__room3d.FMS().현장 === 'SEOUL' && !window.__room3d.나는중()
      && window.__room3d.고른().some(id => (window.__room3d.모형().항목.find(i => i.id === id) || {}).점 === 'CRAC-05')
      && (() => { const R = window.__room3d, it = R.모형().항목.find(i => i.점 === 'CRAC-05'), t = R.controls.target;
                  return Math.hypot(t.x - it.x, t.z - it.y) < 1.5 && R.camera.position.distanceTo(t) < 15; })()"""),
         f"센서 칸 → 3D 서울센터 CRAC-05 고름 ({fr.evaluate('window.__room3d.고른()')})")
    확인(pg.evaluate("document.getElementById('modal').classList.contains('hide') || !document.querySelector('#modal td.go3d')"),
         "팝업은 닫힘")
    pg.wait_for_timeout(1500); pg.screenshot(path=f"{OUT}/d5_장애내역_3D.png")

    # 101차 — 장애예측 목록의 센서를 누르면 3D 상면의 그 센서로 (「CRAC-05 환기온도」 = 서울 배치 CRAC-05)
    fr.select_option("#layoutSel", 부산[0]); 기다리기(fr, "window.__room3d.FMS().현장 === 'BUSAN'")
    pg.evaluate("setMode('predict')"); pg.wait_for_timeout(500)
    pg.wait_for_selector("#predict td.go3d", timeout=10000)
    칸 = pg.locator("#predict td.go3d", has_text="CRAC-05 환기").first
    확인(칸.count() == 1, f"장애예측 목록 — 센서 칸이 누를 수 있음 ({pg.locator('#predict td.go3d').count()}칸)")
    pg.screenshot(path=f"{OUT}/d6_장애예측_센서칸.png")
    칸.click()
    확인(기다리기(fr, """window.__room3d.FMS().현장 === 'SEOUL' && !window.__room3d.나는중()
      && window.__room3d.고른().some(id => (window.__room3d.모형().항목.find(i => i.id === id) || {}).점 === 'CRAC-05')
      && (() => { const R = window.__room3d, it = R.모형().항목.find(i => i.점 === 'CRAC-05'), t = R.controls.target;
                  return Math.hypot(t.x - it.x, t.z - it.y) < 1.5 && R.camera.position.distanceTo(t) < 15; })()"""),
         f"장애예측 센서 → 3D 서울센터 CRAC-05 고름 ({fr.evaluate('window.__room3d.고른()')})")
    확인(pg.evaluate("document.getElementById('modal').classList.contains('hide')"), "추세 그래프 팝업은 안 뜸 (줄 누름과 따로)")
    pg.wait_for_timeout(1500); pg.screenshot(path=f"{OUT}/d7_장애예측_3D.png")

    # 저장 — 이 창 안의 가짜 API 에 남고, 다시 열면 「서버」 배치
    r = pg.evaluate("""fetch('/api/sites/1/room-layout').then(r => r.json()).then(b => b.layout)""")
    확인(r is None, "처음엔 저장된 배치 없음 (기본 배치로 열림)")
    pg.evaluate("""fetch('/api/sites/1/room-layout', {method: 'PUT', body: JSON.stringify({layout: {항목: [], 방: {w: 10, d: 8}}})}).then(r => r.json())""")
    확인(pg.evaluate("fetch('/api/sites/1/room-layout').then(r => r.json()).then(b => !!b.layout && !!b.saved_at)"), "배치 저장 → 같은 창에서 다시 읽힘")

    확인(not 오류, f"콘솔 오류·경고 0건 {오류[:5]}")
    b.close()

print(f"실패 {len(실패)}")
sys.exit(1 if 실패 else 0)
