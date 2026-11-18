# 데모 3D 상면의 공간 사용률 색·요약판·전산실 목록·8방향 시점을 브라우저로 확인하는 시험 (629차)
#
# 사용: python3 room3d_space_check.py [demo.html] [그림 폴더]
# 왜 (2026-11-18, 사용자 「첨부된 파일을 참조하여 3d 상면관리에 추가할 내용이 있으면 컨폼을 받고 추가해」 → 고른 셋)

import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

DEMO = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).with_name("demo.html")).resolve()
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "/tmp")
실패 = []


def 확인(조건, 말):
    print(("✓ " if 조건 else "✗ ") + 말)
    if not 조건:
        실패.append(말)


def 기다리기(fr, 식, timeout=60000):
    try:
        fr.wait_for_function(식, timeout=timeout)
        return True
    except Exception:
        return False


with sync_playwright() as p:
    br = p.chromium.launch(args=["--use-gl=swiftshader", "--enable-unsafe-swiftshader"])
    pg = br.new_page(viewport={"width": 1600, "height": 900})
    오류 = []
    pg.on("pageerror", lambda e: 오류.append(str(e)))
    pg.on("console", lambda m: m.type == "error" and 오류.append(m.text))
    pg.goto(DEMO.as_uri())
    pg.wait_for_timeout(2500)
    pg.click('#menu button[data-mode="room3d"]')
    fr = None
    for _ in range(100):
        fr = next((f for f in pg.frames if f != pg.main_frame and f.url == "about:srcdoc"), None)
        if fr:
            break
        time.sleep(.2)
    확인(fr is not None, "3D 상면 화면이 뜸")
    확인(기다리기(fr, "window.__room3d && window.__room3d.FMS().현장 === 'SEOUL' && window.__room3d.라이브().켬"), "서울센터 실시간 값")

    # 요약판
    확인(기다리기(fr, "window.__room3d.랙공간().length >= 40"), f"랙 용량 등록 랙 읽음 ({fr.evaluate('window.__room3d.랙공간().length')})")
    요약 = fr.evaluate("window.__room3d.요약()") or ""
    붙 = 요약.replace("\n", "").replace(" ", "")
    확인("랙142" in 붙 and "랙용량등록40" in 붙, f"요약판 랙 수(네트워크 랙 2 포함)·등록 수 ({요약[:80]!r})")
    확인(("위급" in 요약 or "장애" in 요약) and "U 전체" in 요약 and "전산실 목록" in 요약, "요약판 U 합계·등급별 알람·전산실 목록")

    # 공간 사용률 색
    fr.select_option("#t_rackmode", "공간")
    pg.wait_for_timeout(800)
    칠 = fr.evaluate("window.__room3d.랙공간().map(id => window.__room3d.공간칠(id))")
    확인(all(x in ("낮음", "보통", "높음") for x in 칠) and len(set(칠)) == 3, f"등록 랙은 세 구간 색 ({sorted(set(칠))})")
    확인(fr.evaluate("window.__room3d.공간칠('R10-01')") is None, "등록 안 된 랙(R10-01)은 칠하지 않음")
    확인(not fr.locator("#rackLg").is_hidden() and "75~100%" in fr.inner_text("#rackLg"), "공간 사용률 범례")
    pg.screenshot(path=f"{OUT}/s1_공간사용률.png")

    # 랙 정보 — 장착 U·실장도
    fr.evaluate("window.__room3d.골라보기(['R01-03'])")
    글 = fr.inner_text("#info")
    확인("장착 U" in 글 and "실장도" in 글 and "U" in 글, f"랙 정보에 장착 U·실장도 ({글[:120]!r})")
    fr.evaluate("window.__room3d.골라보기(['R10-01'])")
    확인("랙 용량에 코드 R10-01" in fr.inner_text("#info"), "등록 안 된 랙은 등록 안내")

    # 8방향 시점
    for v, 조건 in [("fl", "c.x < t.x && c.z > t.z && c.y - t.y > 5"), ("b", "Math.abs(c.x - t.x) < 1 && c.z < t.z"),
                    ("r", "c.x > t.x && Math.abs(c.z - t.z) < 1"), ("br", "c.x > t.x && c.z < t.z")]:
        fr.click(f'#vgrid button[data-v="{v}"]')
        ok = 기다리기(fr, f"!window.__room3d.나는중() && (() => {{ const c = window.__room3d.camera.position, t = window.__room3d.controls.target; return {조건}; }})()", 10000)
        확인(ok, f"시점 단추 {v}")
    pg.screenshot(path=f"{OUT}/s2_뒤오른쪽.png")

    # 전산실 목록 카드 → 다른 현장
    fr.evaluate("document.querySelector('#sumBox details').open = true")
    fr.locator("#sumBox .sc", has_text="부산센터").click()
    확인(기다리기(fr, "window.__room3d.FMS().현장 === 'BUSAN'"), "전산실 목록 카드로 부산센터")
    확인(기다리기(fr, "(window.__room3d.요약() || '').includes('부산센터 요약')"), "요약판도 부산센터로")
    pg.screenshot(path=f"{OUT}/s3_부산.png")

    확인(not 오류, f"콘솔 오류 없음 ({오류[:3]})")
    br.close()

print("실패", len(실패))
sys.exit(1 if 실패 else 0)
