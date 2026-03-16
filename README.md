# 🗞️ IssueFit - 로컬 버전

정치 뉴스 이슈 분석 및 다관점 요약 시스템 (로컬/서버용)

---

## ⚠️ 모델 파일 안내

`models/political_classifier/model.safetensors` (460MB) 는 GitHub 용량 제한으로 저장소에 포함되지 않습니다.  
아래 중 하나로 준비하세요:

- **방법 A (Docker Hub 사용):** `docker-compose.hub.yml` 로 실행하면 모델이 이미 이미지 안에 포함되어 있어 별도 준비 불필요
- **방법 B (직접 빌드):** 모델 파일을 별도로 받아 `models/political_classifier/model.safetensors` 에 배치 후 `docker compose up -d --build`

---

## 🐳 Docker로 빠르게 시작하기 (권장)

다른 PC에서 환경 구성 없이 바로 실행할 수 있습니다.

### 사전 요구사항

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) 설치

### 1단계: 환경 파일 준비

```bash
cp .env.example .env
# .env 파일을 열어 NAVER_CLIENT_ID, NAVER_CLIENT_SECRET 입력
```

### 2단계: 실행

```bash
docker compose up -d
```

최초 실행 시 자동으로 수행됩니다:
- Python 앱 이미지 빌드 (~5-10분)
- Ollama 서버 시작
- gemma2:2b 모델 다운로드 (~1.6GB, 한 번만)

### 3단계: 브라우저에서 열기

```
http://localhost:8501
```

### 파이프라인 실행 (데이터 갱신)

```bash
# 크롤링 → 분류 → 요약 전체 실행
docker compose exec app python pipeline.py --steps 1,3,4

# 특정 단계만 실행
docker compose exec app python pipeline.py --steps 4
```

### 종료 / 재시작

```bash
docker compose down        # 중지
docker compose up -d       # 재시작 (모델 재다운로드 없음)
docker compose logs -f app # 로그 확인
```

---

## 🚀 로컬 직접 실행

### 1. 설치

```bash
# 가상환경 생성 (선택)
python -m venv venv
source venv/bin/activate  # Windows: venv\\Scripts\\activate

# 패키지 설치
pip install -r requirements.txt

# Ollama 설치
curl -fsSL https://ollama.com/install.sh | sh
ollama pull gemma2:2b
```

### 2. API 키 설정 (선택)

```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 편집
nano .env  # 또는 원하는 에디터
```

### 3. 모델 파일 준비

`models/political_classifier/` 폴더에 모델 파일 배치:

```
models/political_classifier/
├── config.json
├── model.pkl (또는 .bin, .pt)
├── label_mapping.json (선택)
└── tokenizer/
    └── ...
```

### 4. 실행

```bash
# 전체 파이프라인 (클러스터링 제외)
python pipeline.py --steps 1,3,4

# UI 실행
streamlit run app.py
```

---

## 📋 전체 워크플로우

```
1️⃣ 크롤링       → data/1_crawled/news.jsonl
2️⃣ 클러스터링   → data/2_clustered/clustered.jsonl (별도 실행)
3️⃣ 정치성향 분류 → data/3_classified/classified.jsonl
4️⃣ 다관점 요약   → data/4_summarized/summaries.json
5️⃣ Streamlit UI → 웹 인터페이스로 결과 확인
```

---

## 📁 폴더 구조

```
IssueFit-Local/
├── modules/               # 핵심 모듈
│   ├── __init__.py
│   ├── crawler.py        # 크롤링
│   ├── classifier.py     # 정치 성향 분류
│   └── summarizer.py     # 다관점 요약
├── app.py                 # Streamlit UI
├── pipeline.py            # 전체 파이프라인
├── .env.example           # API 키 템플릿
├── requirements.txt       # 의존성
└── README.md              # 이 파일

실행 시 생성:
data/
├── 1_crawled/            # 크롤링 결과
├── 2_clustered/          # 클러스터링 결과
├── 3_classified/         # 분류 결과
└── 4_summarized/         # 요약 결과

models/
└── political_classifier/  # 모델 파일 (직접 배치!)
```

---

## 🔧 단계별 실행

### Step 1: 크롤링

```bash
python pipeline.py --steps 1 \\
  --keywords "국회" "대통령" "여야" \\
  --max-articles 100
```

**출력:** `data/1_crawled/news.jsonl`

---

### Step 2: 클러스터링 (별도 실행)

⚠️ 이 단계는 별도의 스크립트나 노트북에서 실행하세요.

**입력:** `data/1_crawled/news.jsonl`  
**출력:** `data/2_clustered/clustered.jsonl`

**방법:**
- Jupyter 노트북 사용
- 또는 별도 클러스터링 Python 스크립트

---

### Step 3: 정치 성향 분류

```bash
python pipeline.py --steps 3 \\
  --model-dir models/political_classifier \\
  --device cuda \\
  --batch-size 32
```

**입력:** `data/2_clustered/clustered.jsonl`  
**출력:** `data/3_classified/classified.jsonl`

---

### Step 4: 다관점 요약

```bash
python pipeline.py --steps 4 \\
  --ollama-model gemma2:2b
```

**입력:** `data/3_classified/classified.jsonl`  
**출력:** `data/4_summarized/summaries.json`

---

### 전체 파이프라인 (1,3,4단계)

```bash
# 한 번에 실행 (클러스터링 제외)
python pipeline.py --steps 1,3,4 \\
  --keywords "국회" "대통령" \\
  --max-articles 50 \\
  --model-dir models/political_classifier
```

---

## 🎨 Streamlit UI

### 실행

```bash
streamlit run app.py
```

브라우저에서 자동으로 열립니다: `http://localhost:8501`

### 기능

1. **이슈 목록**: 모든 정치 이슈 탐색
2. **이슈 상세**: 4가지 관점 요약 (진보/보수/중립/전체)
3. **기사 목록**: 썸네일 + 원문 링크 + 성향 필터
4. **대시보드**: 통계 및 차트
5. **정보**: 프로젝트 소개

---

## ⚙️ 설정 파일 (.env)

```bash
# 네이버 검색 API (선택사항)
NAVER_CLIENT_ID=your_id
NAVER_CLIENT_SECRET=your_secret

# Ollama 설정
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma2:2b

# 크롤링 설정
MAX_ARTICLES_PER_KEYWORD=100
CRAWL_DELAY_SECONDS=0.5
```

---

## 📊 데이터 형식

### 1. 크롤링 결과 (JSONL)

```json
{"title": "...", "content": "...", "url": "...", "thumbnail": "...", "published_at": "..."}
```

### 2. 클러스터링 결과 (JSONL)

```json
{"title": "...", "content": "...", "cluster_id": 0, "cluster_label": "...", ...}
```

### 3. 분류 결과 (JSONL)

```json
{"title": "...", "political_stance": "progressive", "stance_confidence": 0.89, ...}
```

### 4. 요약 결과 (JSON)

```json
{
  "0": {
    "cluster_label": "...",
    "summaries": {
      "progressive": "...",
      "conservative": "...",
      "neutral": "...",
      "overall": "..."
    }
  }
}
```

---

## 🔧 고급 옵션

### 모듈별 실행

```python
# 크롤링만
from modules.crawler import crawl_political_news
crawl_political_news(["국회"], 50, "data/1_crawled/news.jsonl")

# 분류만
from modules.classifier import PoliticalClassifier
classifier = PoliticalClassifier("models/political_classifier")
classifier.classify_and_save("input.jsonl", "output.jsonl")

# 요약만
from modules.summarizer import PoliticalNewsSummarizer
summarizer = PoliticalNewsSummarizer()
summarizer.summarize_and_save("input.jsonl", "output.json")
```

---

## 🐛 문제 해결

### 1. 모델 파일을 찾을 수 없습니다

```bash
# 폴더 구조 확인
ls -la models/political_classifier/

# 필수 파일
# - config.json
# - model.pkl (또는 .bin, .pt)
# - tokenizer/ 폴더
```

### 2. GPU 메모리 부족

```bash
# 배치 크기 줄이기
python pipeline.py --steps 3 --batch-size 16
```

### 3. Ollama 연결 실패

```bash
# Ollama 상태 확인
ollama list

# Ollama 재시작
ollama serve

# 모델 확인
ollama pull gemma2:2b
```

### 4. 포트가 이미 사용 중

```bash
# 다른 포트로 실행
streamlit run app.py --server.port 8502
```

---

## 💡 팁

### 1. 빠른 테스트

```bash
# 적은 데이터로 테스트
python pipeline.py --steps 1,3,4 \\
  --keywords "국회" \\
  --max-articles 20
```

### 2. 백그라운드 실행

```bash
# nohup으로 백그라운드 실행
nohup python pipeline.py --steps 1,3,4 > pipeline.log 2>&1 &

# 로그 확인
tail -f pipeline.log
```

### 3. 가상환경 관리

```bash
# 가상환경 생성
python -m venv venv

# 활성화
source venv/bin/activate  # Linux/Mac
venv\\Scripts\\activate   # Windows

# 비활성화
deactivate
```

---

## 📚 모듈별 상세

### crawler.py

- 네이버 뉴스 크롤링
- URL, 썸네일, 제목, 내용 수집
- 중복 제거
- JSONL 저장

### classifier.py

- BERT + TextCNN 모델
- 진보/보수/중립 분류
- pkl/bin/pt 자동 감지
- 배치 처리

### summarizer.py

- Ollama LLM 요약
- 4가지 관점 (진보/보수/중립/전체)
- 이슈별 3문장 요약
- JSON 저장

---

## ❓ FAQ

### Q: 클러스터링은 왜 별도인가요?
**A:** 클러스터링은 UMAP+HDBSCAN 등 복잡한 라이브러리가 필요하고, 하이퍼파라미터 튜닝이 필요해서 별도 실행을 추천합니다.

### Q: DB 없이 어떻게 작동하나요?
**A:** 각 단계별로 JSONL/JSON 파일을 저장하고, UI에서 직접 읽어서 표시합니다. 데이터가 많지 않으면 문제없습니다.

### Q: 다른 Ollama 모델도 사용할 수 있나요?
**A:** 네! `.env` 파일에서 `OLLAMA_MODEL`을 변경하거나, `--ollama-model` 옵션을 사용하세요.

### Q: 네이버 API가 꼭 필요한가요?
**A:** 아니요! 웹 크롤링만으로도 작동합니다. API는 선택사항입니다.

---

## 🤝 기여

문제를 발견하거나 개선 아이디어가 있으면 이슈를 등록해주세요!

---

## 📄 라이선스

MIT License

---

**IssueFit v1.0 (Local)** | Made with ❤️
