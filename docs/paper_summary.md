# IssueFit 논문 정리 — 크롤러 & 정치성향 분류기

---

## 목차

1. [시스템 개요](#1-시스템-개요)
2. [크롤러 (Crawler)](#2-크롤러-crawler)
   - 2.1 [아키텍처 개요](#21-아키텍처-개요)
   - 2.2 [수집 전략](#22-수집-전략)
   - 2.3 [언론사 분류](#23-언론사-분류)
   - 2.4 [정치 관련성 필터](#24-정치-관련성-필터)
   - 2.5 [본문·메타데이터 추출](#25-본문메타데이터-추출)
3. [정치성향 분류기 (Classifier)](#3-정치성향-분류기-classifier)
   - 3.1 [모델 아키텍처](#31-모델-아키텍처)
   - 3.2 [수식 정리](#32-수식-정리)
   - 3.3 [손실 함수 (Loss Function)](#33-손실-함수-loss-function)
   - 3.4 [학습 설정](#34-학습-설정)
4. [데이터셋](#4-데이터셋)
5. [실험 결과](#5-실험-결과)
6. [버전별 성능 비교](#6-버전별-성능-비교)
7. [파이프라인 전체 구조](#7-파이프라인-전체-구조)

---

## 1. 시스템 개요

IssueFit은 국내 주요 언론사의 정치 뉴스를 자동으로 수집·분류·요약하는 시스템이다.  
전체 파이프라인은 다음 4단계로 구성된다.

```
1단계: 크롤링   → data/1_crawled/news.jsonl
2단계: 클러스터링 → data/2_clustered/clustered.jsonl
3단계: 정치성향 분류 → data/3_classified/classified.jsonl
4단계: 다관점 요약 → data/4_summarized/summaries.json
```

본 문서는 **1단계 크롤러**와 **3단계 정치성향 분류기**를 중심으로 기술한다.

---

## 2. 크롤러 (Crawler)

### 2.1 아키텍처 개요

| 구분 | 내용 |
|------|------|
| 구현 모듈 | `modules/clawler_ver2.py` → `PoliticsNewsCrawler` |
| 주요 라이브러리 | `requests`, `BeautifulSoup4` |
| 데이터 수집 방식 | 네이버 뉴스 검색 API + 개별 기사 URL 직접 크롤링 |
| 출력 형식 | JSONL (기사당 1줄: title, content, url, source, published\_at, media\_stance) |

**API 엔드포인트:**

```
GET https://openapi.naver.com/v1/search/news.json
  ?query={keyword}
  &display={1~100}
  &start={1~1000}
  &sort=date
```

인증 헤더: `X-Naver-Client-Id`, `X-Naver-Client-Secret`

---

### 2.2 수집 전략

#### (1) 키워드 기반 검색

검색 키워드 집합 $\mathcal{Q} = \{q_1, q_2, \ldots, q_K\}$에 대해 API 결과를 페이지네이션으로 수집한다.  
기본 키워드: `정치, 국회, 대통령, 여야, 정당, 선거, 정책, 법안, 국정감사, 여론조사`

#### (2) 균형 크롤링 (Balanced Crawl)

진보·중도·보수 성향 언론사 11곳을 대상으로, 언론사별 쿼터 $N_s^{\max}$를 적용하여 특정 언론사 편중을 방지한다.

$$
n_s \leq N_s^{\max} = \left\lceil \frac{N_{\text{total}}}{|\mathcal{S}|} \right\rceil, \quad s \in \mathcal{S}
$$

- $\mathcal{S}$: 균형 크롤링 대상 언론사 집합 (11곳)  
- $N_{\text{total}}$: 목표 수집 기사 수

#### (3) 폴백(Fallback) 전략

균형 크롤링 결과가 목표치 미달 시 전체 언론사 모드로 자동 전환, 추가 키워드로 보완 수집한다.

---

### 2.3 언론사 분류

| 성향 | 언론사 |
|------|--------|
| 진보 (Progressive) | 한겨레, 경향신문, 오마이뉴스, 프레시안 |
| 중도 (Moderate) | 한국일보, 서울신문, 세계일보 |
| 보수 (Conservative) | 조선일보, 중앙일보, 동아일보, 국민일보 |

**언론사 판별 방식 (우선순위):**

1. URL 도메인 매핑 (`DOMAIN_TO_SOURCE` 딕셔너리)  
2. 네이버 뉴스 URL 내 미디어 코드 (`/article/{3자리코드}/`)  
3. HTML 메타태그 (`og:site_name`, `publisher`)

---

### 2.4 정치 관련성 필터

크롤링된 기사의 제목과 본문을 결합한 텍스트에서 정치 관련 키워드의 등장 횟수를 집계하고, 임계값 $\theta = 2$를 초과하는 기사만 최종 수집한다.

$$
f_{\text{political}}(x) = \mathbf{1}\left[\sum_{w \in \mathcal{W}} \mathbf{1}[w \in x] \geq \theta\right]
$$

- $\mathcal{W}$: 정치 키워드 집합 (국회, 대통령, 정부, 정당, 의원, 선거, 여야, 국정, 법안, 특검, 검찰, 민주당, 국민의힘 등 30개)  
- $\theta = 2$

블랙리스트 도메인(뷰티·스포츠·광고 등)에 해당하는 기사는 사전 필터링으로 제거한다.

---

### 2.5 본문·메타데이터 추출

**본문 추출 셀렉터 (우선순위 순):**

```
#dic_area                     ← 네이버 뉴스 최신
#articleBodyContents          ← 일반 네이버 뉴스
._article_body_contents
#newsEndContents
article / .article_body
```

불필요한 태그(`script, style, .ad, .advertisement, figure, figcaption` 등) 제거 후 순수 텍스트만 추출한다. 최소 100자 이상인 경우에만 유효 본문으로 처리한다.

**발행일 추출 순서:**

1. `meta[property="article:published_time"]`
2. `meta[name="publish_date"]`
3. DOM 셀렉터 (`.media_end_head_info_datestamp em`, `.times`)

---

## 3. 정치성향 분류기 (Classifier)

### 3.1 모델 아키텍처

**구현 클래스:** `KoBigBird_TextCNN_Attention_V7`  
**구현 파일:** `V7_final_fixed6 (2).ipynb` (학습) / `modules/classifier.py` (추론)

전체 아키텍처는 다음 4단계로 구성된다.

```
입력 텍스트 (제목 + 본문)
    │
    ▼
[1] KoBigBird Encoder  ─── 최대 1,024 토큰, hidden_size=768
    │  last_hidden_state: [B, L, 768]
    ▼
[2] Multi-scale TextCNN ── Conv1d × 4 (kernel: 2, 3, 4, 5) + ReLU + MaxPool
    │  concat: [B, 1024]
    ▼
[3] Self-Attention ──────── Multi-Head Attention (8 heads) + Residual + LayerNorm
    │  [B, 1024]
    ▼
[4] FC Classifier ───────── Linear(1024 → 3)
    │
    ▼
logits → softmax → {진보, 중립, 보수}
```

**모델 파라미터 총계:** 120,710,915개 (전체 학습 가능)

---

### 3.2 수식 정리

#### Step 1. KoBigBird 인코딩

사전학습 모델: `monologg/kobigbird-bert-base` (Sparse Attention, 최대 1024/2048 토큰 지원)

$$
\mathbf{H} = \text{KoBigBird}(\mathbf{x}) \in \mathbb{R}^{B \times L \times d}, \quad L = 1024, \; d = 768
$$

KoBigBird는 BigBird의 Sparse Attention 메커니즘을 한국어에 적용한 모델로, 기존 BERT(512 토큰)보다 2배 긴 문맥을 처리할 수 있다.

#### Step 2. TextCNN (다중 커널)

$\mathbf{H}$를 채널 축으로 전치하여 Conv1d 입력으로 변환한다.

$$
\mathbf{H}^T \in \mathbb{R}^{B \times d \times L}
$$

커널 크기 $k \in \{2, 3, 4, 5\}$에 대해:

$$
\mathbf{c}_k = \text{ReLU}\!\left(\text{Conv1d}_{(d \to 256,\; k)}(\mathbf{H}^T)\right) \in \mathbb{R}^{B \times 256 \times L'}
$$

$$
\mathbf{p}_k = \text{MaxPool1d}(\mathbf{c}_k) \in \mathbb{R}^{B \times 256}, \quad L' = L - k + 1
$$

4개의 풀링 결과를 채널 방향으로 연결(concatenate):

$$
\mathbf{h}_{\text{cnn}} = [\mathbf{p}_2 \| \mathbf{p}_3 \| \mathbf{p}_4 \| \mathbf{p}_5] \in \mathbb{R}^{B \times 1024}
$$

#### Step 3. Self-Attention + Residual Connection

$\mathbf{h}_{\text{cnn}}$을 시퀀스 길이 1의 쿼리·키·값으로 확장하여 Multi-Head Self-Attention 적용:

$$
\hat{\mathbf{h}} = \text{MultiHeadAttn}(\mathbf{h}_{\text{cnn}}, \mathbf{h}_{\text{cnn}}, \mathbf{h}_{\text{cnn}}), \quad \text{heads} = 8
$$

Residual connection 및 Layer Normalization 적용:

$$
\mathbf{h}_{\text{att}} = \text{LayerNorm}(\hat{\mathbf{h}} + \mathbf{h}_{\text{cnn}})
$$

이후 Dropout($p=0.3$) 적용.

#### Step 4. 분류 및 추론

$$
\mathbf{z} = W \mathbf{h}_{\text{att}} + \mathbf{b} \in \mathbb{R}^{B \times 3}
$$

$$
\hat{y} = \arg\max_{c} \; \sigma(\mathbf{z})_c, \quad \sigma(\mathbf{z})_c = \frac{e^{z_c}}{\sum_{j=0}^{2} e^{z_j}}
$$

신뢰도(Confidence): $\text{conf} = \max_c \; \sigma(\mathbf{z})_c$

---

### 3.3 손실 함수 (Loss Function)

학습에는 **Combined Loss**를 사용한다.

$$
\mathcal{L} = \lambda \cdot \mathcal{L}_{\text{focal}} + (1 - \lambda) \cdot \mathcal{L}_{\text{smooth}}, \quad \lambda = 0.7
$$

#### (1) Focal Loss

클래스 불균형 문제(중립 40.6%, 보수 33.3%, 진보 26.1%) 완화를 위해 적용한다.

$$
\mathcal{L}_{\text{focal}} = -\alpha_{y_i} (1 - p_t)^{\gamma} \log(p_t)
$$

- $p_t = \exp(-\text{CE}_i)$: 정답 클래스에 대한 예측 확률  
- $\alpha_{y_i}$: 클래스별 가중치 → **진보: 1.3, 중립: 0.7, 보수: 1.0**  
- $\gamma = 2.0$: focusing parameter (쉬운 샘플의 기여를 줄임)

#### (2) Label Smoothing Cross-Entropy

과적합 및 모델 과신(overconfidence) 방지를 위해 정답 라벨을 소프트 분포로 대체한다.

$$
\tilde{y}_c = \begin{cases} 1 - \varepsilon & c = y \\ \dfrac{\varepsilon}{K - 1} & c \neq y \end{cases}, \quad \varepsilon = 0.1, \; K = 3
$$

$$
\mathcal{L}_{\text{smooth}} = -\sum_{c=0}^{K-1} \tilde{y}_c \log p_c
$$

#### (3) Combined Loss 가중치

| 손실 | 비중 |
|------|------|
| Focal Loss | 70% ($\lambda = 0.7$) |
| Label Smoothing CE | 30% ($1 - \lambda = 0.3$) |

---

### 3.4 학습 설정

| 항목 | 값 |
|------|----|
| 사전학습 모델 | `monologg/kobigbird-bert-base` |
| 최대 입력 길이 | 1,024 토큰 |
| 입력 구성 | 제목 + 본문 결합 (`title + " " + content`) |
| 배치 크기 | 4 × gradient accumulation 4 = **실질 16** |
| Learning Rate | 2e-5 |
| LR 스케줄러 | Cosine Annealing with Warmup (warmup ratio: 10%) |
| 옵티마이저 | AdamW, weight decay: 0.01 |
| Gradient Clipping | max\_grad\_norm = 1.0 |
| 에폭 | 최대 10, Early Stopping (patience=3, threshold=0.01) |
| 혼합 정밀도 | FP16 |
| GPU 환경 | Google Colab, Tesla T4 (15.83 GB) |
| 시드 | 42 |

**학습률 스케줄:**

Cosine Annealing with Linear Warmup:

$$
\eta_t = \eta_{\min} + \frac{1}{2}(\eta_{\max} - \eta_{\min})\left(1 + \cos\frac{\pi \cdot t_{\text{decay}}}{T_{\text{decay}}}\right)
$$

- Warmup: 전체 스텝의 10% (약 253 스텝)  
- Total steps: 약 2,530

---

## 4. 데이터셋

### 학습용 데이터 (V7 노트북)

| 파일명 | 용도 | 크기 |
|--------|------|------|
| `complete_train_stratified.csv` | 학습 + 검증 | 4,500개 |
| `complete_test_stratified.csv` | 테스트 | 500개 |

- 검증 데이터: 학습 데이터에서 stratified 10% split → **Train 4,050 / Val 450 / Test 500**

### 라벨 정의

원본 데이터는 5-class 레이블(`label1`)이며, 학습 시 3-class로 병합한다.

| 원본 라벨 | 의미 | 변환 후 |
|-----------|------|---------|
| 1 | 극진보 | 0 (진보) |
| 2 | 진보 | 0 (진보) |
| 3 | 중립 | 1 (중립) |
| 4 | 보수 | 2 (보수) |
| 5 | 극보수 | 2 (보수) |

### 클래스 분포

| 클래스 | Train | Test |
|--------|-------|------|
| 진보 (0) | 1,175개 (26.1%) | 131개 (26.2%) |
| 중립 (1) | 1,828개 (40.6%) | 203개 (40.6%) |
| 보수 (2) | 1,497개 (33.3%) | 166개 (33.2%) |

---

## 5. 실험 결과

### 에폭별 학습 경과

| Epoch | Train Loss | Val Loss | Val Accuracy |
|-------|-----------|----------|-------------|
| 1 | 0.6671 | 0.5741 | 51.11% |
| 2 | 0.5231 | 0.5203 | 65.33% |
| 3 | 0.4766 | 0.5033 | 68.67% |
| 4 | 0.4073 | 0.6069 | 64.67% |
| 5 | 0.3502 | 0.5656 | 68.00% |
| 6 | 0.2908 | 0.6364 | 70.22% |
| 7 | 0.2355 | 0.7523 | 70.67% |
| 8 | 0.1787 | 0.8129 | 70.89% |
| 9 | 0.1568 | 0.8244 | 71.56% |

### 테스트 결과 (500개)

| 클래스 | Precision | Recall | F1-score | Support |
|--------|-----------|--------|----------|---------|
| 진보 | 0.6733 | 0.7710 | 0.7189 | 131 |
| 중립 | 0.7929 | 0.6601 | 0.7204 | 203 |
| 보수 | 0.6796 | 0.7410 | 0.7089 | 166 |
| **macro avg** | **0.7153** | **0.7240** | **0.7161** | 500 |
| **weighted avg** | **0.7239** | **0.7160** | **0.7162** | 500 |

- **검증 정확도: 71.56%**  
- **테스트 정확도: 71.60%**

### 혼동 행렬 (Confusion Matrix)

```
              예측 진보  예측 중립  예측 보수
실제 진보  [  101       10       20  ]
실제 중립  [   31      134       38  ]
실제 보수  [   18       25      123  ]
```

---

## 6. 버전별 성능 비교

| 버전 | 아키텍처 | 분류 클래스 | 테스트 정확도 | 개선폭 |
|------|----------|------------|-------------|--------|
| V5.5 | RoBERTa + TextCNN | 5-class | 57.60% | — |
| V6 | RoBERTa + TextCNN | 3-class | 63.60% | +6.00%p |
| **V7** | **KoBigBird + TextCNN + Attention** | **3-class** | **71.60%** | **+8.00%p** |

**V7 핵심 개선사항 및 기여:**

| 기술 | 역할 | 예상 기여도 |
|------|------|------------|
| KoBigBird (1024 토큰) | 긴 정치 기사 전체 문맥 이해 | +2~4%p |
| Focal Loss | 클래스 불균형 완화 | +2~3%p |
| Self-Attention | 중요 특징 강조 | +2~3%p |
| Label Smoothing | 과적합·과신 방지 | +1~2%p |
| Cosine Annealing | 학습 안정화 | +1%p |

---

## 7. 파이프라인 전체 구조

```
[입력: 검색 키워드]
        │
        ▼
 ┌──────────────────────────────────────────────┐
 │  Step 1. 크롤러 (PoliticsNewsCrawler)         │
 │  - 네이버 뉴스 API 검색                       │
 │  - 균형 크롤링 (11개 언론사, 언론사별 쿼터)    │
 │  - 정치 키워드 필터 (θ=2)                     │
 │  - 본문·메타데이터 추출 (BeautifulSoup)       │
 │  출력: news.jsonl                             │
 └──────────────────────────────────────────────┘
        │
        ▼
 ┌──────────────────────────────────────────────┐
 │  Step 2. 클러스터링 (clusterer.py)            │
 │  - 문서 임베딩 → UMAP 차원 축소 → HDBSCAN    │
 │  출력: clustered.jsonl                        │
 └──────────────────────────────────────────────┘
        │
        ▼
 ┌──────────────────────────────────────────────┐
 │  Step 3. 정치성향 분류 (classifier.py)        │
 │  - KoBigBird + TextCNN + Attention (V7)      │
 │  - Combined Loss (Focal 70% + LabelSmooth 30%)│
 │  - 3-class: 진보 / 중립 / 보수               │
 │  출력: classified.jsonl (stance_confidence 포함)│
 └──────────────────────────────────────────────┘
        │
        ▼
 ┌──────────────────────────────────────────────┐
 │  Step 4. 다관점 요약 (summarizer.py)          │
 │  - Ollama LLM (gemma2:2b 등)                 │
 │  출력: summaries.json                         │
 └──────────────────────────────────────────────┘
        │
        ▼
 [Streamlit UI / FastAPI 서비스]
```

---

## 참고: 주요 의존성

| 패키지 | 버전 | 용도 |
|--------|------|------|
| `torch` | ≥2.0.0 | 딥러닝 프레임워크 |
| `transformers` | ≥4.30.0 | KoBigBird, Tokenizer, Trainer |
| `safetensors` | ≥0.4.0 | 모델 가중치 저장 |
| `requests` | ≥2.31.0 | HTTP 크롤링 |
| `beautifulsoup4` | ≥4.12.0 | HTML 파싱 |
| `scikit-learn` | ≥1.3.0 | 평가 지표 |
| `umap-learn` | ≥0.5.0 | 차원 축소 (클러스터링) |
| `hdbscan` | ≥0.8.0 | 밀도 기반 클러스터링 |
| `pandas` / `numpy` | ≥2.0.0 / ≥1.24.0 | 데이터 처리 |

---

*최종 업데이트: 2026-03-12*
