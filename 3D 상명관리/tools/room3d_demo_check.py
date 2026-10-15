# 단독 데모(demo.html)를 파일로 열어 「3D 상면」 이 서버판처럼 FMS 연결로 도는지 크로미엄으로 본다 — 쓰는 법: python3 room3d_demo_check.py <그림 폴더> [demo.html] (playwright 필요)
#
# 90차 (2026-10-14, 사용자 「지금까지 했는 내용을 demo.html 에 적용. 앞으로 계속 적용해라」)
#   현장 고르기(서울·부산·대전) · 센터 기본 배치 · 데모 센서 값과 알람 · 현장 바꾸기 · 알람의 「3D」 로 그 센서 앞으로 ·
#   배치 저장(이 창 안에서만) · 콘솔 오류 0 을 차례로 본다.
import os, sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = sys.argv[1] if len(sys.argv) > 1 else "demo_shots"
DEMO = Path(sys.argv[2] if len(sys.argv) > 2 else Path(__file__).resolve().parent / "demo.html").resolve()
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
    pg.goto(DEMO.as_uri()); pg.wait_for_timeout(2500)
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

    # 93차 — 장애 내역 팝업의 센서 칸을 누르면 3D 상면의 그 센서로 (「CRAC-05 펌프1」 = 서울 배치 CRAC-05)
    fr.select_option("#layoutSel", 부산[0]); 기다리기(fr, "window.__room3d.FMS().현장 === 'BUSAN'")
    pg.evaluate("setMode('dash')"); pg.wait_for_timeout(500)
    pg.evaluate("showKpiDetail('sensor', '이상이 있는 센서')")
    pg.wait_for_selector("#modal td.go3d", timeout=10000)
    칸 = pg.locator("#modal td.go3d", has_text="CRAC-05 펌프1").first
    확인(칸.count() == 1, "장애 내역 팝업 — 센서 칸이 누를 수 있음")
    pg.screenshot(path=f"{OUT}/d4_장애내역_센서칸.png")
    칸.click()
    확인(기다리기(fr, "window.__room3d.FMS().현장 === 'SEOUL' && window.__room3d.고른().some(id => (window.__room3d.모형().항목.find(i => i.id === id) || {}).점 === 'CRAC-05')"),
         f"센서 칸 → 3D 서울센터 CRAC-05 고름 ({fr.evaluate('window.__room3d.고른()')})")
    확인(pg.evaluate("document.getElementById('modal').classList.contains('hide') || !document.querySelector('#modal td.go3d')"),
         "팝업은 닫힘")
    pg.wait_for_timeout(1500); pg.screenshot(path=f"{OUT}/d5_장애내역_3D.png")

    # 저장 — 이 창 안의 가짜 API 에 남고, 다시 열면 「서버」 배치
    r = pg.evaluate("""fetch('/api/sites/1/room-layout').then(r => r.json()).then(b => b.layout)""")
    확인(r is None, "처음엔 저장된 배치 없음 (기본 배치로 열림)")
    pg.evaluate("""fetch('/api/sites/1/room-layout', {method: 'PUT', body: JSON.stringify({layout: {항목: [], 방: {w: 10, d: 8}}})}).then(r => r.json())""")
    확인(pg.evaluate("fetch('/api/sites/1/room-layout').then(r => r.json()).then(b => !!b.layout && !!b.saved_at)"), "배치 저장 → 같은 창에서 다시 읽힘")

    확인(not 오류, f"콘솔 오류·경고 0건 {오류[:5]}")
    b.close()

print(f"실패 {len(실패)}")
sys.exit(1 if 실패 else 0)
