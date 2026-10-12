<!-- 3D 상면관리(전산실 3D 보기·배치 편집기) 작업 폴더 안내 -->
# 3D 상면관리

전산실을 3D로 보고, 포토샵처럼 랙·공조·센서를 배치하는 화면이다. FMS 본체(`60_monitor_ui/static/room3d.html`)와 같은 파일을 여기에 두어 GitHub에서 바로 열고 고칠 수 있게 했다.

- 바로 열기 → https://ds5tar.github.io/FMS/3D%20상명관리/room3d.html
- 저장소 폴더 → https://github.com/ds5tar/FMS/tree/main/3D%20상명관리

## 파일

| 파일 | 하는 일 |
|---|---|
| `room3d.html` | 화면 전체(보기 + 배치 편집기). 한 파일이다 |
| `room3d_scene.json` | 처음 도면(랙 292·공조·기둥·벽 좌표, 미터 단위) |
| `vendor/three/` | Three.js r185 사본. 폐쇄망에서도 돌도록 CDN 대신 넣었다 |
| `tools/room3d_check.py` | 크로미엄으로 열어 보기·게이지·편집기를 시험한다 |
| `원본_추출/` | 평면도 그림에서 좌표를 뽑던 옛 스크립트와 첫 3D 그림. 원본 평면도 그림은 넣지 않았다 |
| `참조_업체_3D상면관리_20261012.md` | 업체 제품 기능 조사 |

## 내 PC에서 열기

파일을 두 번 눌러 열면 모듈을 못 불러 하얗게 나온다. 웹 서버로 연다.

```
cd "3D 상명관리"
python -m http.server 8000
```

브라우저에서 http://localhost:8000/room3d.html 을 연다.

## 쓰는 법

- 보기 — 휠은 마우스 쪽 확대, 두 번 누르면 그 자리로, 미니맵 누르기·끌기, 찾기(R123·C1·AC05), 키보드 WASD·QE·+−·F·Home
- 시점 게이지 — X·Y·Z·회전·기울기·확대를 1 cm·0.1° 단위까지 조절
- 배치 편집 — 메뉴(파일·편집·보기·정렬), 도구(이동 V·사각 선택 M·회전 R·손 H·돋보기 Z·벽 B·자 I), 패널(장비·레이어·속성·작업 내역)
- 장비 29종 — 랙·공조·전력·센서 13종·건축·바닥을 끌어 놓는다
- 저장 — Ctrl+S는 브라우저에 저장, 「JSON 내려받기·열기」로 파일로 주고받는다

GitHub Pages에서 고친 배치는 그 브라우저에만 저장된다. 다른 PC와 나누려면 JSON으로 내려받아 넘긴다.

## 고친 뒤 시험

```
pip install playwright && python -m playwright install chromium
python "3D 상명관리/tools/room3d_check.py" "3D 상명관리" 시험그림
```

마지막 줄이 `실패 0`이어야 한다. 지금 판은 모두 통과하고 콘솔 오류·경고는 0건이다.

## FMS 본체와 맞추기

원본은 PC의 `C:\claude\FMS\60_monitor_ui\static\`에 있다. 여기서 고친 것은 그 폴더에 다시 넣어야 FMS 서버 화면에도 들어간다. 거꾸로 PC에서 고치면 이 폴더에 다시 올린다.
