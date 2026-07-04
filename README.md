# SignalFeed

글로벌 매크로 경제 뉴스를 분석해 한국 증시 영향(섹터 단위)을 추론하고,
Instagram 카드뉴스를 자동 생성하는 AI 콘텐츠 파이프라인입니다.

## Pipeline
RSS/Finnhub 수집 → UMAP+HDBSCAN 클러스터링 → Gemini 2.5 Flash 구조화 생성
→ 코드 레벨 검증 → Playwright 렌더링 (1080x1350 카드뉴스 5장)

## 기술적 특징

- **무료 API만으로 구성** — Gemini free tier, Pixabay, Finnhub free tier.
  유료 서비스 없이 매일 자동으로 도는 프로덕션 파이프라인 설계
- **LLM 출력을 신뢰하지 않는 아키텍처** — 섹터-근거 정합성, 콘텐츠 중복,
  예측/권유 표현을 전부 코드 레벨 validator로 강제 검증. 검증 실패 시
  자동 교정 또는 안전한 fallback으로 전환
- **구조적 안전장치** — Pydantic enum으로 티커/회사명 노출을 스키마
  레벨에서 원천 차단 (프롬프트 지시가 아닌 타입 시스템으로 강제)
- **비용 관리** — LLM 응답 캐싱으로 반복 렌더링 시 API 호출 0회,
  일일 쿼터 20 req 내에서 운영
- **레퍼런스 학습 시스템** — 벤치마크 콘텐츠(인스타/유튜브)를 자동
  수집·분석해 디자인·훅 패턴을 축적, 생성 프롬프트에 반영

## Tech Stack
Python · Google Gemini API · scikit-learn / UMAP / HDBSCAN ·
Playwright · Pydantic · yfinance

## 개발 방식

이 프로젝트는 Claude Code를 페어 프로그래밍 파트너로 두고 개발했습니다.
매 세션의 작업 배경과 판단 근거는 `CLAUDE.md`에 기록해가며 진행했고,
커밋에는 Co-Authored-By 표기가 그대로 남아 있습니다 — 굳이 감출 이유가
없는 협업 방식이라 그대로 드러냅니다.

아키텍처 결정, 검증 로직 설계, 버그의 근본 원인 진단은 직접 주도했습니다.
예를 들어 초기 버전은 "섹터와 이유가 안 맞으면 안 된다"를 프롬프트 지시로만
막고 있었는데, 실제 카드 산출물을 검토하다 "바이오·제약" 섹터에 "보험·운용
자산 수익률"이라는 이유가 붙어 나오는 걸 발견했습니다. 원인을 추적해보니
섹터 enum에 '보험'이라는 항목 자체가 없어 LLM이 이유를 엉뚱한 섹터에
붙이고 있었고, 이를 걸러낼 검증 로직도 없었습니다. 이 사례를 계기로
"LLM 출력은 신뢰하지 않는다"는 원칙을 세우고, 섹터-이유 정합성·콘텐츠
중복·출처 정제 같은 검증을 프롬프트가 아니라 코드 레벨 validator로
강제하도록 구조를 바꿨습니다.

이런 판단들은 세션 단위로 `CLAUDE.md`와 [docs/session_archive.md](docs/session_archive.md)에
전부 기록되어 있습니다.

## Sample Output
카드뉴스 5장 구조 (커버 → 팩트 → 수혜 섹터 → 주의 섹터 → 결론)

| ![1](docs/assets/sample_1.png) | ![2](docs/assets/sample_2.png) | ![3](docs/assets/sample_3.png) |
|---|---|---|
| ![4](docs/assets/sample_4.png) | ![5](docs/assets/sample_5.png) | |

---
개인 프로젝트 · 진행 중
