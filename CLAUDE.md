# CLAUDE.md — SignalFeed Project

> **SignalFeed (시그널피드)** — 글로벌 경제 뉴스를 호재/악재/중립 시그널로 압축하는 AI 콘텐츠 자동화 플랫폼
> Pipeline: Collect (RSS+Finnhub) → Cluster (UMAP+HDBSCAN) → Generate (Gemini 구조화 출력) → Render (Playwright 카드 5장) → Shorts (MoviePy)

---

## 1. Project Overview

**SignalFeed**는 글로벌 매크로 경제 뉴스를 분석해 한국 주식시장 영향(섹터 단위)을 추론하고,
Instagram 카드뉴스 5장 + YouTube Shorts를 자동 생성하는 플랫폼입니다.

### Goals
1. **수집**: RSS (Reuters/Bloomberg/NYT) + Finnhub API로 매크로 경제 뉴스만 수집 (키워드 필터)
2. **클러스터링**: TF-IDF + UMAP + HDBSCAN으로 이슈 그룹화 (English-optimized)
3. **생성**: Gemini 2.5 Flash 구조화 출력(JSON schema)으로 훅 타이틀 + 슬라이드 콘텐츠 생성
4. **검증**: 규칙+yfinance 팩트 체크, 섹터-이유 정합성, 중복 제거, 출처 정제 (전부 구조적/코드 레벨)
5. **렌더링**: Python HTML 빌더 + Playwright로 1080x1350 카드 5장 PNG
6. **배포**: MVP는 로컬 저장 후 수동 업로드 (자동화는 Phase 2)

### Target Users
- 한국 MZ세대 투자자 (20-35세) — 시각적 콘텐츠, 빠른 소비
- 해외 경제 뉴스를 한국어로 소비하려는 구독자

### Architecture Philosophy
- **File-based pipeline**: DB 없음. 모든 중간 결과는 JSONL/JSON 파일
- **Modular**: 각 단계 독립 실행 가능 (`--steps 1,2,3,4`)
- **Free-only**: 유료 API/서비스 금지. Gemini free tier, Pixabay, Finnhub free, yfinance
- **Structural guarantees**: 티커 금지·섹터 정합성·중복 제거는 프롬프트가 아닌 **코드(enum/validator)로 차단**

---

## 2. Tech Stack

| 영역 | 기술 | 비고 |
|------|------|------|
| Language | Python 3.10+ (venv) | `venv/bin/python` 사용 |
| 수집 | feedparser (RSS), finnhub-python | Finnhub 무료 60 req/min |
| 클러스터링 | scikit-learn, umap-learn, hdbscan, pandas | |
| 콘텐츠 생성 | **google-genai** (Gemini 2.5 Flash) | 무료 티어 — **일일 쿼터 매우 작음(실측 ~20 req/day)**, 호출 최소화 + 캐시 필수 |
| 스키마 강제 | pydantic (`response_schema`) | 섹터명 enum → 티커/회사명 구조 차단 |
| 팩트 검증 | yfinance + 규칙 테이블 | `fact_checker.py` |
| 배경 이미지 | **Pixabay API** | 무료, `PIXABAY_API_KEY` 필요, 실패 시 단색 fallback |
| 카드 렌더링 | Python HTML 빌더 + Playwright (Chromium) | 1080x1350, device_scale_factor=2, Pretendard CDN |
| Shorts | moviepy, gTTS, matplotlib, mplcyberpunk, yfinance | 1080x1920, ~55초 |

**제거된 것들** (Session 44 정리): EXAONE/Ollama, FinBERT(torch/transformers), GPT-4o-mini auto labeling,
Pexels, Pillow 카드 생성, 정치 뉴스 크롤러 일체. 자세한 내역은 `docs/audit_session44.md`.

### Environment Variables (.env)
- `FINNHUB_API_KEY` (필수 — 수집)
- `GEMINI_API_KEY` (선택 — 없으면 큐레이션 fallback 콘텐츠로 동작)
- `PIXABAY_API_KEY` (선택 — 없으면 단색 배경 fallback)
- `IG_SESSION_FILE` / `IG_USERNAME` (선택 — 벤치마크 발굴용 instaloader 세션, 없으면 익명 시도)

---

## 3. File Structure

```
issuefit_project/            # 레포 이름 유지 (SignalFeed 프로젝트)
├── backend/
│   ├── modules/
│   │   ├── collector.py         # 뉴스 수집 (RSS + Finnhub, 매크로 키워드 필터)
│   │   ├── clusterer.py         # 이슈 클러스터링 (TF-IDF + UMAP + HDBSCAN)
│   │   ├── content_gen.py       # Gemini 구조화 출력 → CardScript (훅+슬라이드 콘텐츠), 캐시 연동
│   │   ├── content_validator.py # 구조 검증: 섹터-이유 정합성, 중복, 출처 정제, 금지어
│   │   ├── card_renderer.py     # CardScript → HTML 5장 (커버 + 내지, 크리미 베이지 #E8E5DF)
│   │   ├── fact_checker.py      # 규칙 + yfinance 팩트 검증 (enum 섹터 ↔ 룰 토큰 alias)
│   │   ├── gen_cache.py         # Gemini 결과 캐시 (material hash → JSON, quota 보호)
│   │   ├── image_fetcher.py     # Pixabay 검색 (키워드 매핑 + 왜곡 이미지 필터 스코어링)
│   │   ├── hook_patterns.py     # 레퍼런스 훅 패턴 로드 → 프롬프트 주입
│   │   └── shorts_gen.py        # YouTube Shorts (매크로 차트 + TTS)
│   ├── reference/               # 레퍼런스 시스템 '코드' (데이터는 루트 reference/)
│   │   ├── discover.py          # 벤치마크 자동 발굴 (engagement/조회수 비율 상위 선별)
│   │   └── collect.py           # 선별 게시물 이미지/메타 수집 (instaloader/yt-dlp)
│   ├── pipeline.py              # CLI: 1 collect → 2 cluster → 3 generate → 4 cards → 5 shorts
│   ├── generate_cards.py        # 카드 렌더링 단독 실행 (scripts.json → PNG)
│   └── scheduler.py             # APScheduler placeholder (Phase 2)
├── reference/                   # 레퍼런스 시스템 '데이터' (코드는 backend/reference/)
│   ├── accounts.txt             # 발굴 대상 계정 (ig:계정명 / yt:채널URL)
│   ├── urls.txt                 # 벤치마크 URL (discover가 append, 수동 추가 가능)
│   ├── discovered.json          # 발굴 결과 (지표 + 선정 사유)
│   ├── patterns.json            # 추출된 디자인/훅 패턴 토큰 (축적)
│   ├── ANALYZE.md               # Claude Code 세션이 직접 이미지 분석하는 절차
│   └── raw/, failed.log         # 수집 미디어·실패 로그 (gitignored)
├── data/                        # 파이프라인 산출물 (gitignored)
│   ├── 1_collected/news.jsonl
│   ├── 2_clustered/clustered.jsonl
│   ├── 3_generated/scripts.json
│   ├── 4_cards/  5_shorts/  cache/  temp/
├── outputs/                     # 리뷰용 렌더 결과 (gitignored)
├── tests/                       # pytest (fixtures 포함)
├── docs/                        # DECISIONS, audit, session_archive
├── requirements.txt
└── CLAUDE.md
```

### Data Flow
1. `data/1_collected/news.jsonl` → 2. `data/2_clustered/clustered.jsonl` →
3. `data/3_generated/scripts.json` (+ `data/cache/gen/*.json`) → 4. `data/4_cards/cluster_X/slide_*.png` → 5. `data/5_shorts/*.mp4`

### Running
```bash
venv/bin/python backend/pipeline.py --steps 1,2,3,4   # 전체 파이프라인
venv/bin/python backend/generate_cards.py             # 카드만 재렌더 (캐시/기존 scripts.json 사용, API 호출 0)
venv/bin/python -m pytest tests/ -q                   # 테스트
```

---

## 4. Key Design Decisions (현행)

1. **Gemini 2.5 Flash 단일 호출 + 구조화 출력** — 클러스터당 1회 호출로 훅+내지 콘텐츠 전부 생성.
   Pydantic `response_schema`로 섹터명을 `KoreanSector` enum으로 강제 → 티커/회사명 출력 자체가 불가능.
   쿼터가 작으므로(실측 ~20 req/day) 결과는 `gen_cache`에 저장, 디자인 반복 시 호출 0회.
2. **검증은 코드로** — LLM 출력은 신뢰하지 않는다. `content_validator`가 (a) 섹터-이유 키워드 정합성
   (b) 슬라이드 간 중복 (c) 출처 화이트리스트 정제 (d) 예측/권유 금지어를 렌더링 전에 강제.
   검증 실패 시 해당 항목 drop/remap, 복구 불가 시 큐레이션 fallback.
3. **팩트 체크** — `fact_checker`가 매크로 토픽 감지 → 룰 테이블(수혜/주의 섹터) + yfinance 추세 대조.
   failed → 섹터 교체, warning → 면책 강화.
4. **카드뉴스 공장 방식** — Slide 1(커버)은 고정 템플릿(Pixabay+다크), Slide 2~5는 구조화 데이터를
   Python 빌더가 렌더. 디자인 수정 = 코드 수정 (LLM 재호출 불필요).
5. **디자인** — 미니멀 크리미 베이지: 내지 배경 **#E8E5DF + grain 텍스처** (Session 43 확정, 순백 금지),
   커버/결론은 다크 #0D0D0D. 폰 기준 큰 텍스트, 커버는 어그로 훅(순한국어). 1080x1350 (4:5), 5장.
   색상 단일 출처는 `card_renderer.py`의 디자인 토큰 상수.
6. **JSONL/JSON 파일 파이프라인** — DB 없음, grep 가능, 단계별 재실행 용이.
7. **클러스터 필터** — 2개 이상 소스에서 보도된 이슈만 통과 (단일 소스 클러스터 제거, clusterer 내장).

---

## 5. Absolute Rules

### Legal & Content
1. **기사 원문 그대로 복제 금지** — 팩트 추출 + 패러프레이즈만
2. **모든 콘텐츠에 면책 포함** — "본 콘텐츠는 AI 분석 정보이며 투자 권유가 아닙니다"
3. **소스 화이트리스트** — Reuters/Bloomberg/CNBC/FT/WSJ/MarketWatch/AP/NYT만. 블로그/SNS 금지
4. **예측/권유 표현 금지** — "예상/전망/오를 것/추천/매수/매도" 금지 (validator가 차단). 과거형 팩트 + 인용만
5. **티커·회사명 노출 금지** — 섹터/업종명만 (`KoreanSector` enum으로 구조 차단)
6. **수치 없는 핵심 팩트 금지** — 모든 핵심 문장에 구체적 숫자
7. **무료만** — 유료 API/서비스 도입 금지

### Engineering
8. **API 키 커밋 금지** — `.env`는 gitignore, 키는 환경변수로만
9. **데이터/산출물 커밋 금지** — `data/`, `outputs/`는 gitignored. 테스트 데이터는 `tests/fixtures/`
10. **pytest** — 핵심 로직(검증/캐시/스키마)은 회귀 테스트 필수. 커밋 전 `pytest` 실행
11. **PEP 8 + type hints + Google docstring**, 파일 IO는 항상 `encoding='utf-8'`
12. **logging 모듈 사용** (print 금지), API 호출은 try/except + 백오프
13. **커밋 메시지** — `<type>: <설명>` (한국어/영어 허용, 이모지 금지)

### Session Log 작성 규칙 (Session 44~)
- CLAUDE.md에는 **세션당 5~10줄 요약만** "Recent Sessions"에 추가 (오래된 항목은 아카이브로 이동)
- 상세 로그는 `docs/session_archive.md`에 추가
- CLAUDE.md 전체 크기는 **40k chars 이내 유지**

---

## 6. Known Issues / Next Steps
- shorts_gen 차트 영상은 정적 이미지 기반 (애니메이션 차트는 추후) — Session 44에서 의도적으로 미수정
- 클러스터링 노이즈 비율 높음 (~64%) — 파라미터 튜닝은 추후
- Instagram/YouTube 자동 업로드 — Phase 2
- 레퍼런스 분석: 수집/패턴 스키마 골격만 구축됨 — 실제 벤치마크 URL 수집·분석 누적 필요

---

## Recent Sessions

> 전체 로그: `docs/session_archive.md` (Sessions 1~43)

- **S41–43**: 카드뉴스 공장 방식(커버 고정 + 내지 생성), Gemini 구조화 출력 전환, `KoreanSector` enum 티커 차단, fact_checker 연동, grain 텍스처
- **S44 (2026-06-12)**: 전면 재구축 — 상세는 아래

### Session 44: 전면 재구축 (컨텍스트 위생 + 결함 해결 + 레퍼런스 시스템)
- CLAUDE.md 144k→10k자 다이어트, 세션 로그 `docs/session_archive.md` 이전, 로그 작성 규칙 신설
- 죽은 코드 ~5,000 LOC 삭제 (정치뉴스 레거시/FinBERT/Pillow 카드 등), torch/transformers 의존성 제거, data/ 산출물 128파일 untrack — `docs/audit_session44.md`
- 생성 경로 단일화: Gemini 클러스터당 1회 호출(기존 2회), 자유 HTML 폐기 → 구조화 데이터 + `card_renderer`
- 실물 카드 결함 5종 구조적 해결: `content_validator`(섹터-이유 정합성/중복/출처 정제/금지어/한국어 커버), flex:1 레이아웃, 이미지 스코어링 — 회귀 테스트로 재발 차단
- `gen_cache`: 캐시 적중 시 Gemini·yfinance 호출 0회 (quota 보호)
- 레퍼런스 분석 골격: `reference/` (urls.txt → collect.py → 세션 직접 분석 → patterns.json → 훅 프롬프트 주입)
- pytest 86개 통과, fixture 렌더 검증본 `outputs/session44_review/` — 중대 결정 전부 `docs/DECISIONS_S44.md`
- **S44 hotfix**: gen_cache가 fallback 결과까지 캐시해 quota 회복 후에도 fallback에 갇히던 버그 수정 — Gemini 성공만 캐시, 오염 캐시는 로드 시 무시·삭제 (회귀 테스트 6개, 총 92개 통과)
- **S45 (2026-06-12)**: 벤치마크 자동 발굴 `discover.py` (계정별 engagement/조회수 비율 상위 5개 → discovered.json + urls.txt, `--collect` 연동) + 픽스 5건 (커버 키워드 토픽 1순위 `TOPIC_KEYWORDS`, 디자인 색상 #E8E5DF 단일화, reference/ 코드·데이터 이원화 명시, Maintainer 이메일 제거, pipeline 로그 표기) + .env.example 현행화 — pytest 115개 통과

---

**Last Updated**: 2026-06-12
**Version**: 2.1 (SignalFeed)
**Maintainer**: joon1216
