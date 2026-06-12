# 레퍼런스 분석 절차 (Claude Code 세션용)

벤치마크 콘텐츠의 디자인·훅 패턴을 **구조화 토큰**으로 추출해 `reference/patterns.json`에 축적한다.
비전 분석은 외부 API 없이 **Claude Code 세션이 직접 이미지를 Read해서** 수행한다 (비용 0).

## 1. 수집
```bash
# reference/urls.txt에 벤치마크 URL 추가 후:
venv/bin/python backend/reference/collect.py
# → reference/raw/{slug}/ 에 이미지/썸네일 저장 (gitignored)
```
- Instagram: instaloader (공개 게시물, 로그인 불필요)
- YouTube: yt-dlp (썸네일 + 메타데이터만, 영상 다운로드 안 함)
- 도구 미설치 시 해당 URL은 건너뛰고 안내만 출력

## 2. 분석 (Claude Code 세션에서)
1. `reference/raw/` 의 이미지를 Read 도구로 직접 열어 본다
2. 각 이미지에서 다음을 관찰한다:
   - **hook**: 표지 문구의 구조 (질문형/수치형/대비형/명령형), 줄바꿈 위치, 글자 수
   - **layout**: 그리드/블록 구조, 여백 분배, 번호·아이콘 사용
   - **typography**: 크기 위계, 굵기 대비, 강조 방식 (하이라이트/컬러/크기)
   - **color**: 배경/포인트 컬러 규칙, 의미-컬러 매핑
   - **thumbnail** (YouTube): 얼굴/텍스트/화살표 등 클릭 유도 요소
3. 관찰을 `patterns.json` 스키마로 추가한다 (id 중복 금지, source_url 기록)
4. 같은 패턴이 여러 벤치마크에서 반복 관찰되면 examples에 사례를 누적한다

## 3. 반영 (자동)
- `backend/modules/hook_patterns.py`가 `type=="hook"` 패턴을 읽어
  content_gen의 Gemini 프롬프트에 자동 주입한다 (패턴 없으면 주입 생략)
- layout/color/typography 패턴은 `card_renderer.py` 수정 시 참고 자료로 사용

## 주의
- 벤치마크 이미지는 분석용으로만 사용 (재배포 금지, reference/raw는 gitignored)
- 패턴은 "구조"만 추출 — 벤치마크의 문구/콘텐츠를 복제하지 않는다
