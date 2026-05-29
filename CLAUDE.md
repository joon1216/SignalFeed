# CLAUDE.md — SignalFeed Project

> **SignalFeed (시그널피드)** — 글로벌 경제 뉴스를 호재/악재/중립 시그널로 압축하는 AI 콘텐츠 자동화 플랫폼  
> AI-powered pipeline: Collect → Cluster → Classify (Signal) → Generate (Instagram Cards + YouTube Shorts)

---

## 1. Project Overview & Goals

**SignalFeed**는 글로벌 경제 뉴스를 자동으로 수집·분석하여 Instagram 카드 뉴스와 YouTube Shorts로 자동 생성·배포하는 AI 콘텐츠 플랫폼입니다.

### Primary Goals
1. **Global Economic News Collection**: Polygon.io + Finnhub API로 Reuters/Bloomberg/FT 등 신뢰도 높은 영문 소스 수집
2. **Issue Clustering**: 유사 뉴스를 이슈별로 그룹화 (UMAP + HDBSCAN)
3. **Signal Classification**: BERT + TextCNN + Attention으로 호재(bullish)/악재(bearish)/중립(neutral) 3-class 분류
4. **Auto Labeling**: GPT-4o-mini API로 학습 데이터 자동 레이블링
5. **Content Generation**: EXAONE 3.5 LLM으로 Instagram 5-slide 카드 뉴스 + YouTube Shorts 60초 스크립트 생성
6. **Auto Distribution**: Instagram API + YouTube API로 자동 업로드 (Phase 5.6-5.7)

### Target Users
- **한국 MZ세대 투자자** (20-35세): 빠른 정보 소비, 시각적 콘텐츠 선호
- **경제 뉴스 구독자**: 해외 뉴스를 한국어로 소비하고 싶은 사용자
- **자산 관리 관심층**: ETF/주식/채권/원자재 등 글로벌 시장 모니터링 필요

### Business Model
- **Phase 1 (MVP)**: Instagram + YouTube 무료 배포 → 팔로워 확보
- **Phase 2**: 뉴스레터 유료 구독 (Substack/Stibee) — 심화 분석 제공
- **Phase 3**: 프리미엄 API (기업/투자사 대상 실시간 시그널 제공)

### Architecture Philosophy
- **File-based pipeline**: 데이터베이스 의존성 없음, 모든 중간 결과는 JSONL/JSON 파일로 저장
- **Modular design**: 각 단계(수집/클러스터링/분류/생성)는 독립적으로 실행 가능
- **Service-oriented structure**: Backend/frontend 분리로 유연한 배포 (로컬/클라우드/컨테이너)
- **Fact-constrained prompts**: SHAP-style 절대 제약으로 hallucination 방지 (기사 원문만 사용, 예측 금지)

---

## 2. Tech Stack

### Core Language & Framework
- **Python 3.10**: 모든 모듈 및 파이프라인 오케스트레이션
- **Streamlit 1.28+**: 관리자 대시보드 (콘텐츠 검수용)

### Machine Learning & NLP
- **PyTorch 2.0+**: 딥러닝 프레임워크
- **Transformers 4.30+**: BERT 모델 백본
- **scikit-learn**: TF-IDF 벡터화
- **UMAP**: 차원 축소 (클러스터링)
- **HDBSCAN**: 밀도 기반 클러스터링
- **EXAONE 3.5 (LG AI)**: 한국어 특화 무료 LLM (콘텐츠 생성)

### Data Collection
- **Polygon.io API**: 미국 주식 뉴스 (Reuters/Bloomberg/AP 등)
- **Finnhub API**: 글로벌 경제 뉴스 (Financial Times/CNBC/MarketWatch 등)
- **Auto Labeling**: GPT-4o-mini API (bullish/bearish/neutral 레이블 자동 생성)

### Content Generation
- **EXAONE 3.5**: 한국어 요약 생성 (무료, LG AI)
- **Pillow + ImageMagick**: Instagram 카드 이미지 생성 (1080x1920px, 5장)
- **MoviePy + gTTS**: YouTube Shorts 영상 생성 (60초, AI 음성)

### Deployment & DevOps
- **Local execution**: Python 가상환경 직접 실행
- **Cloud deployment ready**: AWS Lambda / Google Cloud Functions 배포 가능
- **APScheduler**: 주기적 크롤링 (Phase 6.1)

### External APIs
- **Polygon.io**: 뉴스 데이터 API (무료 플랜: 5 req/min)
- **Finnhub**: 글로벌 뉴스 API (무료 플랜: 60 req/min)
- **OpenAI GPT-4o-mini**: 자동 레이블링 ($0.15/1M tokens)
- **Instagram Graph API**: 자동 포스팅 (Phase 5.6)
- **YouTube Data API v3**: Shorts 업로드 (Phase 5.7)

---

## 3. File Structure

```
issuefit_project/  (레포 이름 유지 - SignalFeed 프로젝트)
│
├── backend/                   # Backend services and pipeline
│   ├── modules/              # Core functional modules
│   │   ├── __init__.py
│   │   ├── collector.py     # News collector (Polygon.io + Finnhub) — NEW
│   │   ├── auto_labeler.py  # GPT-4o-mini auto labeling — NEW
│   │   ├── clusterer.py     # Issue clustering (TF-IDF + UMAP + HDBSCAN) — REUSE
│   │   ├── classifier.py    # Signal classifier (BERT + TextCNN + Attention) — RETRAIN
│   │   ├── content_gen.py   # Content generator (EXAONE 3.5) — NEW
│   │   ├── card_gen.py      # Instagram card image generator (Pillow) — NEW
│   │   ├── shorts_gen.py    # YouTube Shorts video generator (MoviePy) — NEW
│   │   ├── fake_filter.py   # 5-layer fake news defense — NEW
│   │   └── summarizer.py    # Legacy summarizer (deprecated)
│   ├── pipeline.py          # CLI orchestrator: all 7 steps
│   └── scheduler.py         # APScheduler: periodic crawling (Phase 6.1)
│
├── frontend/                  # Frontend application
│   └── app.py                # Streamlit admin dashboard (content review)
│
├── models/                    # Pre-trained models
│   └── signal_classifier/    # Signal classifier (bullish/bearish/neutral)
│       ├── config.json        # Model configuration
│       ├── model.safetensors  # Model weights (retrain from political_classifier)
│       ├── label_mapping.json # Class labels: bullish/bearish/neutral
│       └── tokenizer/         # Tokenizer files
│
├── data/                      # Pipeline outputs (created at runtime)
│   ├── 1_collected/
│   │   └── news.jsonl        # Raw collected articles (Polygon.io + Finnhub)
│   ├── 2_labeled/
│   │   └── labeled.jsonl     # Auto-labeled data (GPT-4o-mini)
│   ├── 3_clustered/
│   │   └── clustered.jsonl   # Clustered articles with cluster_id/cluster_label
│   ├── 4_classified/
│   │   └── classified.jsonl  # Articles with signal/confidence (bullish/bearish/neutral)
│   ├── 5_generated/
│   │   └── scripts.json      # Generated content scripts (Instagram + YouTube)
│   ├── 6_cards/
│   │   └── cluster_0/        # Instagram card images (5 slides per issue)
│   │       ├── slide_1.png
│   │       ├── slide_2.png
│   │       ├── slide_3.png
│   │       ├── slide_4.png
│   │       └── slide_5.png
│   └── 7_shorts/
│       └── cluster_0.mp4     # YouTube Shorts video (60sec)
│
├── tests/                     # Test suite (TODO: pytest)
│   └── __init__.py
│
├── docs/                      # Documentation
│   ├── content_format.md     # Instagram 5-slide format spec
│   ├── narrative_structure.md # STOCKER-style 3-step narrative
│   └── color_system.md       # Dark mode color palette
│
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variable template
├── .gitignore                 # Excludes large model files & data
├── README.md                  # User documentation (Korean)
└── CLAUDE.md                  # This file
```

### Key File Descriptions

**Backend Modules**
- `collector.py` (NEW): Polygon.io + Finnhub API 호출, 영문 뉴스 수집, 화이트리스트 필터링
- `auto_labeler.py` (NEW): GPT-4o-mini로 bullish/bearish/neutral 자동 레이블링 (학습 데이터 생성)
- `clusterer.py` (REUSE): TF-IDF + UMAP + HDBSCAN, IssueFit에서 재사용
- `classifier.py` (RETRAIN): BERT + TextCNN + Attention, political → signal 레이블로 재학습
- `content_gen.py` (NEW): EXAONE 3.5로 Instagram 5-slide 스크립트 + YouTube Shorts 스크립트 생성
- `card_gen.py` (NEW): Pillow로 Instagram 카드 이미지 생성 (1080x1920px, dark mode)
- `shorts_gen.py` (NEW): MoviePy + gTTS로 YouTube Shorts 영상 생성 (60초, AI 음성)
- `fake_filter.py` (NEW): 5-layer defense (whitelist → cross-validation → LLM screening → anomaly → disclaimer)

**Frontend**
- `frontend/app.py`: Streamlit 관리자 대시보드 (콘텐츠 검수, 수동 편집, 배포 승인)

**Data Flow**
- Step 1: Collect → `data/1_collected/news.jsonl`
- Step 2: Auto Label → `data/2_labeled/labeled.jsonl` (GPT-4o-mini)
- Step 3: Cluster → `data/3_clustered/clustered.jsonl`
- Step 4: Classify → `data/4_classified/classified.jsonl` (signal)
- Step 5: Generate → `data/5_generated/scripts.json` (EXAONE 3.5)
- Step 6: Card → `data/6_cards/cluster_X/slide_*.png` (Instagram)
- Step 7: Shorts → `data/7_shorts/cluster_X.mp4` (YouTube)

---

## 4. Development Status

### Phase-Based Progress

| Phase | Component | Status | Notes |
|-------|-----------|--------|-------|
| **Phase 1-4: IssueFit (Legacy)** |
| 1.1-4.3 | Political news pipeline | ✅ Deprecated | Pivot to SignalFeed |
| **Phase 5: SignalFeed Rebuild** |
| 5.1 | Docker Removal & Restructure | ✅ Complete | Backend/frontend separation |
| 5.2 | CLAUDE.md Full Rewrite (Pivot) | ✅ Complete | Project pivot to SignalFeed |
| 5.3 | Data Pipeline Rebuild | ⬜ Planned | Polygon.io + Finnhub integration |
| 5.4 | BERT Retraining | ⬜ Planned | Retrain classifier (bullish/bearish/neutral) |
| 5.5 | Content Generation Pipeline | ⬜ Planned | EXAONE 3.5 + card/shorts generation |
| 5.6 | Instagram Auto-Upload | ⬜ Planned | Instagram Graph API integration |
| 5.7 | YouTube Shorts Auto-Upload | ⬜ Planned | YouTube Data API v3 integration |
| **Phase 6: Advanced Features** |
| 6.1 | APScheduler Integration | ⬜ Planned | Periodic crawling (every 4 hours) |
| 6.2 | Newsletter Module | ⬜ Planned | Stibee/Substack integration |
| 6.3 | Premium API Server | ⬜ Planned | FastAPI for enterprise clients |
| 6.4 | A/B Testing Framework | ⬜ Planned | Content performance analytics |

### Current Milestone
**v2.0 (SignalFeed MVP)** — Pivot from political news to global economic signals, Instagram + YouTube automation.

---

## 5. Key Design Decisions

### Architecture

**1. Source Whitelist (Polygon.io + Finnhub Only)**
- **Decision**: Only use Polygon.io and Finnhub as news sources
- **Rationale**: Ensures high-quality sources (Reuters/Bloomberg/FT), avoids copyright issues, minimizes fake news risk
- **Tradeoff**: Lower volume vs. scraping all sources, API rate limits (Polygon: 5 req/min, Finnhub: 60 req/min)

**2. GPT-4o-mini for Auto Labeling**
- **Decision**: Use GPT-4o-mini ($0.15/1M tokens) to auto-label bullish/bearish/neutral
- **Rationale**: No manual annotation needed, scalable, cost-effective ($0.15 for ~6,600 articles)
- **Tradeoff**: Label noise (~5-10% error rate), requires validation set for quality control

**3. EXAONE 3.5 (LG AI) for Content Generation**
- **Decision**: Use EXAONE 3.5 instead of GPT-4/Claude for summarization
- **Rationale**: Free API (LG AI Research), Korean-specialized (better than GPT-4 for Korean), no cost ceiling
- **Tradeoff**: Slightly lower quality vs. GPT-4o, requires LG AI account, potential rate limits

**4. Fact-Constrained Prompts (STOCKER-style)**
- **Decision**: Enforce fact-only extraction, ban prediction/recommendation expressions
- **Rationale**: Prevents hallucination, reduces legal liability, aligns with STOCKER narrative structure
- **Tradeoff**: Less engaging content vs. opinionated commentary, requires strict prompt engineering

**5. 5-Layer Fake News Defense**
- **Decision**: Whitelist → Cross-validation → LLM screening → Anomaly detection → Disclaimer
- **Rationale**: Multi-layer defense reduces fake news propagation to <1%, builds user trust
- **Tradeoff**: Higher computational cost, may filter out legitimate edge-case news

### Content Format

**6. Instagram 5-Slide Card News**
- **Decision**: Fixed 5-slide format (cover → bullish → bearish → neutral → CTA)
- **Rationale**: Consistent UX, optimized for Instagram algorithm, easy to scan
- **Tradeoff**: Less flexibility vs. variable-length posts, may feel formulaic

**7. YouTube Shorts 60sec**
- **Decision**: AI voice (gTTS) + signal visuals, 60sec max
- **Rationale**: Shorts algorithm favors <60sec, AI voice reduces production cost, scales to 10+ videos/day
- **Tradeoff**: Lower production quality vs. human narration, robotic voice may reduce engagement

**8. Dark Mode Only (#121212 Background)**
- **Decision**: Dark mode UI (#121212 background, #00C853 bullish, #FF3D3D bearish)
- **Rationale**: MZ generation preference, better for night viewing, signal colors stand out
- **Tradeoff**: Less visibility in bright environments, may alienate users who prefer light mode

### Model & Algorithms

**9. BERT + TextCNN + Attention (Reuse from IssueFit)**
- **Decision**: Retrain same architecture, change labels from political → signal
- **Rationale**: Proven architecture (F1 ~0.85 on political data), transfer learning from financial domain
- **Tradeoff**: Requires retraining (~10K labeled samples), may not outperform fine-tuned FinBERT

**10. UMAP + HDBSCAN Clustering (Reuse from IssueFit)**
- **Decision**: Reuse clustering pipeline without modification
- **Rationale**: Works well for news clustering (validated in IssueFit), no domain-specific tuning needed
- **Tradeoff**: May over-cluster breaking news (too many small clusters), under-cluster evergreen topics

### Data Processing

**11. JSONL for All Intermediate Data**
- **Decision**: Continue using JSONL (newline-delimited JSON) for all pipeline outputs
- **Rationale**: Streaming-friendly, easy to inspect, grep-friendly, no DB setup
- **Tradeoff**: No schema enforcement, harder to query complex relationships

**12. No Newsletter in MVP (Instagram + YouTube Only)**
- **Decision**: Exclude newsletter from Phase 5, launch with Instagram + YouTube only
- **Rationale**: Faster MVP, newsletter requires email list + Stibee/Substack integration, focus on social first
- **Tradeoff**: No direct subscriber revenue in MVP, harder to monetize without newsletter

---

## 6. Absolute Rules

### Legal & Risk Management

**1. NEVER Reproduce Article Text Verbatim**
- ALWAYS extract facts only (JSON structured output: {fact, source, timestamp})
- NEVER copy-paste entire paragraphs from Reuters/Bloomberg/FT (copyright violation)
- Use extractive summarization (key sentences only) + paraphrasing

**2. ALWAYS Include Disclaimer**
- EVERY Instagram post MUST include: "본 콘텐츠는 AI 분석 정보이며 투자 권유가 아닙니다"
- EVERY YouTube Shorts MUST show disclaimer in first 3 seconds + description
- No exception for "obvious" neutral content

**3. Source Whitelist Only**
- ONLY use news from: Polygon.io, Finnhub, Reuters, Bloomberg, Financial Times, Wall Street Journal
- NEVER scrape unverified blogs, Twitter, Reddit, Telegram
- If source not in whitelist → auto-reject

**4. Minimum 3-Source Validation**
- Before publishing ANY issue, minimum 3 independent sources must report same event
- If only 1-2 sources → label as "unconfirmed" + hide from public feed
- Cross-validation logic in `fake_filter.py`

**5. No Prediction Expressions Allowed**
- BANNED words in generated content: "예상", "전망", "오를 것", "떨어질 것", "추천", "매수", "매도"
- ALLOWED: "상승했다" (past tense), "발표했다" (fact), "분석가는 X라고 말했다" (attribution)
- LLM prompt MUST enforce this constraint (system prompt + output validation)

### Testing

**6. Pytest Required for New Modules**
- ALL new modules in `backend/modules/` MUST have corresponding `tests/backend/modules/test_X.py`
- Minimum coverage: 70% for content generation, 90% for fake_filter
- Run `pytest` before every commit to main

**7. A/B Testing for Content Variants**
- EVERY Instagram post generates 2 variants (A/B) with different headlines
- Track engagement (likes/comments/shares) for 24h, select winner for YouTube Shorts
- Log A/B results to `data/ab_results.jsonl`

### Git

**8. Never Commit API Keys**
- `.env` MUST be in `.gitignore`
- POLYGON_API_KEY, FINNHUB_API_KEY, OPENAI_API_KEY, INSTAGRAM_ACCESS_TOKEN → NEVER commit
- Use GitHub Secrets for CI/CD, local `.env` for development

**9. Commit Messages (Korean/English 모두 허용)**
- Format: `<Component>: <Action> <Details>` (예: `feat: Polygon.io API 연동 완료`, `fix: 클러스터링 버그 수정`)
- No emoji in commits

**10. Tag Releases for Model Checkpoints**
- When retraining classifier → tag as `v2.X-model` (e.g., `v2.1-model-signal-classifier`)
- Include model card in tag message (F1 score, training data size, hyperparameters)

### Coding Conventions

**11. Python Style (PEP 8)**
- 4-space indents, snake_case for functions/variables
- Docstrings for all public functions (Google style)
- Type hints REQUIRED for new modules (e.g., `def collect_news(api_key: str) -> List[Dict]`)

**12. File Encoding (UTF-8)**
- ALWAYS use `encoding='utf-8'` when reading/writing files
- Korean text in prompts/outputs requires UTF-8

**13. Error Handling**
- Wrap API calls in try/except with exponential backoff (max 3 retries)
- Log all API errors to `logs/api_errors.log`
- NEVER silently swallow exceptions

**14. Environment Variables**
- REQUIRED: `POLYGON_API_KEY`, `FINNHUB_API_KEY`, `OPENAI_API_KEY`
- OPTIONAL: `EXAONE_API_KEY`, `INSTAGRAM_ACCESS_TOKEN`, `YOUTUBE_API_KEY`
- Load via `python-dotenv`

**15. Logging**
- Use `logging` module (not print) for all backend modules
- Log levels: DEBUG (API raw responses), INFO (pipeline progress), WARNING (rate limits), ERROR (API failures)
- Rotate logs daily (`logs/pipeline_YYYYMMDD.log`)

**16. Project Structure Conventions**
- Backend code MUST add project root to sys.path
- New modules go in `backend/modules/`, tests in `tests/backend/modules/`
- Generated content goes in `data/6_cards/` (Instagram) and `data/7_shorts/` (YouTube)

**17. Content Format Standards**
- Instagram cards: 1080x1920px PNG, 5 slides, dark mode (#121212 background)
- YouTube Shorts: 1080x1920px MP4, 60sec max, AI voice (gTTS Korean)
- JSON keys: `issue_id`, `signal` (bullish/bearish/neutral), `confidence`, `script`, `sources`

---

## 7. Research Notes

### Deep Research Results (2026-05-29)

**1. Project Pivot Decision**
- **Original**: IssueFit (Korean political news, progressive/conservative/neutral)
- **New**: SignalFeed (global economic news, bullish/bearish/neutral)
- **Pivot Reason**:
  - Political domain blocked by Meta algorithm (shadowban risk on Instagram)
  - Copyright risk with Korean news outlets (Naver/Daum/Chosun strict DMCA)
  - Limited monetization (political = low CPM, high controversy)
  - Economic signals = higher engagement with MZ investors + newsletter revenue potential

**2. EXAONE 3.5 Selection**
- **Alternatives Considered**: GPT-4o ($15/1M tokens), Claude 3.5 Sonnet ($3/1M tokens), Gemini 2.0 Flash (free but rate-limited)
- **Why EXAONE 3.5**: Free API, Korean-specialized (LG AI trained on 한국어 corpus), competitive quality with GPT-4 for Korean
- **Risk**: LG AI may introduce rate limits or paid tiers later → fallback to Gemini 2.0 Flash

**3. STOCKER Project Reference**
- **Source**: STOCKER project (한국 주식 뉴스 분석 플랫폼, 2023)
- **Adopted**: Fact-constrained prompt structure (phenomenon → fact → open conclusion)
- **Adopted**: 3-step narrative (no prediction, user judgment delegation)
- **Adopted**: Disclaimer enforcement (legal protection)

**4. Fake News Defense System**
- **5 Layers**:
  1. **Whitelist**: Polygon.io, Finnhub, Reuters, Bloomberg, FT only
  2. **Cross-validation**: Minimum 3 sources must agree
  3. **LLM screening**: GPT-4o-mini checks for contradictions/anomalies
  4. **Anomaly detection**: Statistical outlier filter (e.g., "Apple stock +500% in 1 day")
  5. **Disclaimer**: All content marked as "AI analysis, not investment advice"
- **Expected Error Rate**: <1% fake news propagation (vs. 5-10% for single-layer whitelist)

**5. UI/UX Design (Confirmed)**
- **Color System**:
  - Background: #121212 (darkest)
  - Surface: #1A1A1A (cards)
  - Card: #2C2C2C (elevated)
  - Bullish: #00C853 (signal green)
  - Bearish: #FF3D3D (signal red)
  - Neutral: #666666 (gray)
  - Brand accent: Signal green only (no multi-color branding)
- **Typography**: Pretendard (Korean) + Inter (English), 14-18px body, 24-32px headlines
- **Instagram Format**: 5-slide fixed format (cover → bullish → bearish → neutral → CTA)

### Current Research Questions

**1. Auto Labeling Accuracy**
- What is GPT-4o-mini's F1 score on bullish/bearish/neutral classification?
- How much training data needed to match human annotation quality?
- Can we use weak supervision (financial market data) to improve labels?

**2. EXAONE 3.5 vs. GPT-4o Quality**
- Quantitative comparison (ROUGE, BLEU) on Korean financial summaries
- Human evaluation (coherence, accuracy, engagement) for Instagram scripts
- Cost-benefit analysis (free EXAONE vs. $15/1M GPT-4o)

**3. Instagram Algorithm Optimization**
- What hashtags maximize reach for economic content? (#경제 #투자 #주식 #ETF)
- Optimal posting time for Korean MZ users (21:00-23:00 KST?)
- Carousel vs. single-image posts (5-slide carousel expected to perform better)

**4. YouTube Shorts Retention**
- AI voice (gTTS) vs. human narration: retention rate comparison
- 30sec vs. 60sec: which length maximizes completion rate?
- Signal visuals (charts/icons) vs. text-only: engagement metrics

### Experiments to Run

**1. A/B Testing: Headline Variants**
- Generate 2 headline variants per issue (conservative vs. sensational)
- Measure engagement (likes/comments/shares) for 24h
- Select winner for YouTube Shorts thumbnail

**2. Classification Model Comparison**
- FinBERT (Hugging Face pre-trained) vs. retrained BERT + TextCNN + Attention
- Training data size: 1K vs. 5K vs. 10K labeled samples
- F1 score, inference speed, model size

**3. Clustering Hyperparameter Tuning**
- HDBSCAN min_cluster_size: 2 vs. 3 vs. 5 (optimal for economic news?)
- UMAP n_components: 10 vs. 30 vs. 50 (financial text dimensionality)
- TF-IDF max_features: 5K vs. 10K vs. 20K

**4. Content Generation Prompt Engineering**
- EXAONE 3.5: zero-shot vs. few-shot (3 examples) vs. chain-of-thought
- Fact-extraction accuracy: JSON output vs. natural language
- Hallucination rate: baseline vs. fact-constrained prompt

### Future Improvements

**1. Real-Time Market Data Integration**
- Integrate Polygon.io stock prices API (real-time AAPL/TSLA/NVDA price overlay on cards)
- Show % change in Instagram cards (e.g., "AAPL +2.3% ↑")
- Annotate bullish/bearish signals with market confirmation

**2. Advanced NLP**
- Named Entity Recognition (NER): extract companies, sectors, countries mentioned
- Sentiment intensity scoring: "slightly bullish" vs. "strongly bullish"
- Event extraction: earnings reports, M&A, regulatory changes

**3. User Features**
- User-submitted feedback: "Was this signal accurate?" (thumbs up/down)
- Personalized signal feed: user selects sectors (tech/healthcare/energy)
- Push notifications: breaking news alerts for followed topics

**4. Performance Optimization**
- Cache BERT embeddings (avoid recomputing for same articles)
- Batch API calls to Polygon.io/Finnhub (reduce latency)
- Pre-generate Instagram cards (overnight pipeline, publish at 21:00 KST)

**5. Evaluation Framework**
- Collect 100 human-labeled samples (bullish/bearish/neutral) for validation
- Compute precision/recall/F1 for signal classifier
- Track Instagram/YouTube engagement metrics (likes, comments, shares, saves)
- Survey MZ users: "How useful is this content?" (1-5 Likert scale)

---

## Notes

- **GitHub Repository**: https://github.com/joon1216/issuefit_project (Public, 레포 이름 유지)
- **Project Pivot (2026-05-29)**: Fully pivoted from IssueFit (political news) to SignalFeed (economic signals)
- **MVP Target**: Instagram 5-slide cards + YouTube Shorts automation (Phase 5.3-5.7)
- **Model Retraining**: BERT + TextCNN + Attention classifier (political → signal labels), target F1 ≥ 0.80
- **API Costs**: Polygon.io (free), Finnhub (free), GPT-4o-mini ($0.15/1M tokens), EXAONE 3.5 (free)
- **Legal Disclaimer**: All generated content MUST include "본 콘텐츠는 AI 분석 정보이며 투자 권유가 아닙니다"
- **Fake News Defense**: 5-layer system (whitelist → cross-validation → LLM screening → anomaly → disclaimer), target <1% error rate
- **Content Format**: Instagram (1080x1920px PNG, 5 slides, dark mode), YouTube Shorts (1080x1920px MP4, 60sec, AI voice)
- **Running the project**: `python backend/pipeline.py --steps 1,3,4,5,6,7` (from project root)

---

## Session Log

### 2026-05-29

#### Session 1: Initial Setup
- **Task**: Initial GitHub repository setup and CLAUDE.md creation
- **Actions**:
  - Created comprehensive CLAUDE.md documentation (390 lines)
  - Updated remote URL from beakwol/issuefit_project to joon1216/issuefit_project
  - Verified .gitignore excludes model.safetensors (460MB) and .env (sensitive)
  - Pushed initial commit to GitHub
- **Result**: ✅ Success — Repository live at https://github.com/joon1216/issuefit_project

#### Session 2: Phase 5.1 — Docker Removal & Restructure
- **Task**: Remove Docker dependencies and restructure project for service deployment
- **Actions**:
  - Deleted Docker files: Dockerfile, docker-compose.yml, docker-compose.hub.yml, .dockerignore
  - Created new structure: `backend/` (modules + pipeline + scheduler), `frontend/` (app.py), `tests/`
  - Moved modules → backend/modules, pipeline.py → backend/, app.py → frontend/
  - Fixed imports: added sys.path management in pipeline.py and app.py
  - Updated backend/modules/__init__.py to use lazy imports
  - Created scheduler.py placeholder, tests/__init__.py
  - Updated CLAUDE.md: File Structure, Tech Stack, Design Decisions, Development Status (Phase 5.1 ✅)
- **Verification**:
  - ✓ Syntax validation: `python -m py_compile backend/pipeline.py` ✅
  - ✓ Syntax validation: `python -m py_compile frontend/app.py` ✅
  - ✓ Directory structure confirmed (backend/modules/, frontend/, tests/)
- **Result**: ✅ Success — Project restructured for flexible deployment

#### Session 3: Phase 5.2 — Full Project Pivot to SignalFeed
- **Task**: Complete project pivot from IssueFit (political news) to SignalFeed (economic signals)
- **Actions**:
  - FULLY rewrote CLAUDE.md (440+ lines):
    - New project name: SignalFeed (시그널피드)
    - New tagline: "글로벌 경제 뉴스를 호재/악재/중립 시그널로 압축하는 AI 콘텐츠 자동화 플랫폼"
    - New tech stack: Polygon.io + Finnhub (news), GPT-4o-mini (auto labeling), EXAONE 3.5 (content gen)
    - New content format: Instagram 5-slide cards + YouTube Shorts 60sec
    - New classification labels: bullish/bearish/neutral (was progressive/conservative/neutral)
    - New target users: Korean MZ generation investors (20-35)
  - Updated Tech Stack section:
    - Replaced Naver API → Polygon.io + Finnhub
    - Replaced Ollama → EXAONE 3.5 (LG AI, free, Korean-specialized)
    - Added GPT-4o-mini for auto labeling
    - Added Pillow + MoviePy for content generation
  - Updated File Structure:
    - New modules: collector.py, auto_labeler.py, content_gen.py, card_gen.py, shorts_gen.py, fake_filter.py
    - New data flow: 7 steps (collect → label → cluster → classify → generate → card → shorts)
    - New model directory: signal_classifier (was political_classifier)
  - Updated Development Status:
    - Phase 1-4 marked as "Deprecated" (IssueFit legacy)
    - Phase 5.2 marked as "✅ Complete" (CLAUDE.md rewrite)
    - Phase 5.3-5.7 added (data pipeline, BERT retrain, content gen, Instagram, YouTube)
    - Phase 6.1-6.4 added (scheduler, newsletter, premium API, A/B testing)
  - Added Absolute Rules:
    - Legal: NEVER reproduce text verbatim, ALWAYS include disclaimer, source whitelist only, minimum 3-source validation, no prediction expressions
    - Testing: pytest required (70-90% coverage), A/B testing for content variants
  - Added Research Notes:
    - Deep Research results: pivot decision, EXAONE selection, STOCKER reference, fake news defense
    - UI/UX design confirmed: dark mode (#121212), signal colors (#00C853 bullish, #FF3D3D bearish)
    - Instagram format confirmed: 5-slide fixed format
  - Added Session Log: Phase 5.2 pivot entry
- **Result**: ✅ Success — CLAUDE.md fully rewritten for SignalFeed project

#### Session 4: CLAUDE.md Minor Fixes
- **Task**: Fix 3 minor errors in CLAUDE.md
- **Actions**:
  - Fixed Rule #9 "Commit Messages": Korean only → Korean/English 모두 허용
    - Updated format example: `feat: Polygon.io API 연동 완료`, `fix: 클러스터링 버그 수정`
  - Fixed APScheduler phase number: Phase 5.2 → Phase 6.1 (3 occurrences)
  - Fixed repo name note: "will rename to signalfeed_project" → "레포 이름 유지" (2 occurrences)
- **Result**: ✅ Success — CLAUDE.md errors corrected

---

**Last Updated**: 2026-05-29  
**Version**: 2.0 (SignalFeed MVP)  
**Maintainer**: joon1216 (rlawnsdudrlawnsdud1216@gmail.com)
