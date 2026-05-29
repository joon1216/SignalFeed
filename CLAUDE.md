# CLAUDE.md — IssueFit Project

> **IssueFit** — Political news issue analysis and multi-perspective summarization system  
> AI-powered pipeline: Crawl → Cluster → Classify (Political Stance) → Summarize (Multi-perspective)

---

## 1. Project Overview & Goals

**IssueFit** is an end-to-end political news analysis system that automates the entire workflow from data collection to multi-perspective summarization.

### Primary Goals
1. **Automated News Collection**: Crawl political news from major Korean news outlets (balanced across progressive/moderate/conservative)
2. **Issue Clustering**: Group similar news articles into coherent political issues using UMAP + HDBSCAN
3. **Political Stance Classification**: Classify articles into progressive/conservative/neutral using BERT + TextCNN + Attention
4. **Multi-Perspective Summarization**: Generate 4 distinct summaries per issue (progressive/conservative/neutral/overall) using Ollama LLM
5. **Interactive Web UI**: Present results via Streamlit dashboard with filtering, search, and drill-down capabilities

### Target Users
- Researchers analyzing media bias and political discourse
- Citizens seeking balanced perspectives on political issues
- Journalists tracking coverage patterns across different outlets

### Architecture Philosophy
- **File-based pipeline**: No database dependency, all intermediate results stored as JSONL/JSON files
- **Modular design**: Each step (crawl/cluster/classify/summarize) is independent and can be run separately
- **Docker-first deployment**: One-command setup with Docker Compose for reproducibility

---

## 2. Tech Stack

### Core Language & Framework
- **Python 3.10**: All modules and pipeline orchestration
- **Streamlit 1.28+**: Web UI dashboard

### Machine Learning & NLP
- **PyTorch 2.0+**: Deep learning framework
- **Transformers 4.30+**: BERT model backbone
- **scikit-learn**: TF-IDF vectorization
- **UMAP**: Dimensionality reduction for clustering
- **HDBSCAN**: Density-based clustering algorithm
- **Ollama + gemma2:2b**: Local LLM for summarization

### Data Processing
- **pandas/numpy**: Data manipulation
- **BeautifulSoup4**: HTML parsing for web scraping
- **requests**: HTTP client for crawling

### Deployment & DevOps
- **Docker + Docker Compose**: Containerized deployment
- **Ollama container**: Separate service for LLM inference
- **Streamlit server**: Web UI container

### External APIs
- **Naver Search API**: News search endpoint (optional, fallback to direct crawling)

---

## 3. File Structure

```
issuefit_project/
│
├── app.py                     # Streamlit web UI (main entry point)
├── pipeline.py                # Orchestrates all 4 steps (crawl/cluster/classify/summarize)
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variable template
├── Dockerfile                 # App container definition (Python + PyTorch CPU)
├── docker-compose.yml         # Multi-container orchestration (app + ollama + init)
├── docker-compose.hub.yml     # Alternative: uses pre-built Docker Hub image
├── .gitignore                 # Excludes large model files & data
├── .dockerignore              # Minimizes Docker build context
│
├── modules/                   # Core functional modules (~2700 LOC total)
│   ├── __init__.py
│   ├── clawler_ver2.py       # News crawler (Naver API + scraping, balanced collection)
│   ├── clusterer.py          # Issue clustering (TF-IDF + UMAP + HDBSCAN)
│   ├── classifier.py         # Political stance classifier (BERT + TextCNN + Attention)
│   ├── summarizer.py         # Multi-perspective summarization (Ollama LLM)
│   ├── crawler.py            # Legacy crawler (v1)
│   ├── crawler_v3.py         # Experimental crawler (v3)
│   └── db_loader.py          # Database loader (unused in current file-based version)
│
├── models/                    # Pre-trained classification model
│   └── political_classifier/
│       ├── config.json        # Model configuration
│       ├── model.safetensors  # Model weights (460MB, NOT in Git)
│       ├── label_mapping.json # Class labels (progressive/conservative/neutral)
│       └── tokenizer/         # Tokenizer files (vocab.txt, tokenizer.json, etc.)
│
├── data/                      # Pipeline outputs (created at runtime)
│   ├── 1_crawled/
│   │   └── news.jsonl        # Raw crawled articles (Step 1 output)
│   ├── 2_clustered/
│   │   └── clustered.jsonl   # Clustered articles with cluster_id/cluster_label (Step 2 output)
│   ├── 3_classified/
│   │   └── classified.jsonl  # Articles with political_stance/stance_confidence (Step 3 output)
│   └── 4_summarized/
│       └── summaries.json    # Multi-perspective summaries by cluster_id (Step 4 output)
│
└── docs/                      # Documentation
    ├── paper_summary.md       # Technical documentation (crawler + classifier architecture)
    └── outlet_crawler_plan.md # Design notes for outlet-specific crawlers
```

### Key File Descriptions

**Root Scripts**
- `app.py` (719 LOC): Streamlit UI with dark theme, issue cards, stance badges, article thumbnails, multi-select filters, Plotly charts
- `pipeline.py` (411 LOC): CLI orchestrator with argparse, supports `--steps 1,3,4`, `--all-sources`, `--mock-classify`, `--skip-summarize`

**Modules**
- `clawler_ver2.py`: Balanced crawler across 11 outlets (4 progressive + 3 moderate + 4 conservative), fallback to all sources if <100 articles, deduplication by URL
- `clusterer.py`: TF-IDF (word + char n-grams) → UMAP (n_components adaptive to sample size) → HDBSCAN (min_cluster_size=2 for small datasets)
- `classifier.py`: `BertTextCNNAttention` model with 4 conv layers (filter sizes 2/3/4/5) + multi-head attention + layer norm + dropout
- `summarizer.py`: LangChain + Ollama integration, generates 4 summaries per cluster (progressive/conservative/neutral/overall) with prompt templates

**Data Flow**
- Each step writes to its numbered directory (`1_crawled/`, `2_clustered/`, etc.)
- JSONL format for line-by-line processing of articles (supports streaming)
- JSON format for final summaries (structured by cluster_id)

---

## 4. Development Status

### Phase-Based Progress

| Phase | Component | Status | Notes |
|-------|-----------|--------|-------|
| **Phase 1: Core Pipeline** |
| 1.1 | News Crawler (v1) | ✅ Complete | Basic scraping, superseded by v2 |
| 1.2 | News Crawler (v2) | ✅ Complete | Balanced 11-outlet collection, fallback logic |
| 1.3 | News Crawler (v3) | ⚠️ Experimental | Outlet-specific parsing (not in main pipeline) |
| 1.4 | Issue Clustering | ✅ Complete | TF-IDF + UMAP + HDBSCAN, adaptive params for small datasets |
| 1.5 | Political Stance Classifier | ✅ Complete | BERT + TextCNN + Attention, 3-class classification |
| 1.6 | Multi-Perspective Summarization | ✅ Complete | Ollama LLM integration, 4 summaries per issue |
| **Phase 2: Deployment** |
| 2.1 | Streamlit UI | ✅ Complete | Dark theme, issue cards, stance filters, thumbnails |
| 2.2 | Docker Containerization | ✅ Complete | Multi-container (app + ollama + init) |
| 2.3 | Docker Hub Distribution | ✅ Complete | `beakwol/issuefit:latest` published |
| 2.4 | Environment Configuration | ✅ Complete | `.env` support for API keys, Ollama settings |
| **Phase 3: Model & Data** |
| 3.1 | Model Training | ✅ Complete | BERT + TextCNN + Attention trained on political corpus |
| 3.2 | Model Export | ✅ Complete | safetensors format (460MB) |
| 3.3 | Test Data | ✅ Complete | `test_classified.jsonl` for UI demo without full pipeline |
| **Phase 4: Documentation** |
| 4.1 | README (Korean) | ✅ Complete | Docker quickstart, local setup, troubleshooting |
| 4.2 | Technical Docs | ✅ Complete | `paper_summary.md` with architecture details |
| 4.3 | CLAUDE.md | ✅ Complete | This file |
| **Phase 5: Future Enhancements** |
| 5.1 | Real-time Monitoring | ⬜ Planned | Cron-based periodic crawling |
| 5.2 | Database Backend | ⬜ Planned | SQLite/PostgreSQL for historical data |
| 5.3 | API Server | ⬜ Planned | FastAPI for programmatic access |
| 5.4 | Advanced Clustering | ⬜ Planned | Hierarchical topic models, temporal clustering |
| 5.5 | Multilingual Support | ⬜ Planned | English translation, cross-lingual models |

### Current Milestone
**v1.0 (Local)** — File-based pipeline with Docker deployment, suitable for single-user research and demos.

---

## 5. Key Design Decisions

### Architecture

**1. File-Based Pipeline (No Database)**
- **Decision**: Store all intermediate results as JSONL/JSON files
- **Rationale**: Simplifies deployment, eliminates DB setup/migration overhead, easy to inspect/debug intermediate states
- **Tradeoff**: Not suitable for large-scale production (lacks indexing, query optimization, concurrent access)

**2. Docker-First Deployment**
- **Decision**: Primary deployment via Docker Compose, local setup as secondary option
- **Rationale**: Ensures reproducibility across environments, bundles Ollama LLM service, avoids "works on my machine" issues
- **Tradeoff**: Requires Docker knowledge, larger initial download (~2GB for Ollama + models)

**3. Modular Step Execution**
- **Decision**: Each pipeline step can run independently via `--steps` flag
- **Rationale**: Faster iteration (e.g., re-run summarization without re-crawling), easier debugging, selective testing
- **Tradeoff**: Requires manual file path coordination if steps run out of order

**4. Balanced Crawler with Fallback**
- **Decision**: Default to 11 balanced outlets (4 progressive + 3 moderate + 4 conservative), fallback to all sources if <100 articles
- **Rationale**: Ensures diverse political perspectives, mitigates single-outlet bias, but adapts to low-data scenarios
- **Tradeoff**: May dilute topic focus in fallback mode (broader keyword search)

### Model & Algorithms

**5. BERT + TextCNN + Attention for Classification**
- **Decision**: Hybrid architecture (contextual embeddings + convolutional feature extraction + attention)
- **Rationale**: BERT captures semantics, TextCNN extracts n-gram patterns, attention focuses on salient features
- **Tradeoff**: Higher computational cost vs. pure BERT, more hyperparameters to tune

**6. Ollama (Local LLM) for Summarization**
- **Decision**: Use Ollama + gemma2:2b instead of cloud APIs (OpenAI, Claude)
- **Rationale**: No API costs, data privacy, offline capability, reproducible results
- **Tradeoff**: Lower summarization quality vs. GPT-4/Claude, requires ~2GB disk + ~4GB RAM

**7. UMAP + HDBSCAN for Clustering**
- **Decision**: Non-parametric density-based clustering vs. k-means
- **Rationale**: Auto-detects number of clusters, handles noise, better for varying cluster shapes
- **Tradeoff**: Sensitive to hyperparameters (min_cluster_size, min_samples), can label all points as noise if tuned poorly

### Data Processing

**8. TF-IDF Vectorization (Word + Char n-grams)**
- **Decision**: Combine word (1-2 grams) and char (2-4 grams) TF-IDF with 2:1 weighting
- **Rationale**: Word n-grams capture semantic similarity, char n-grams handle typos/informal text, dual representation improves clustering recall
- **Tradeoff**: Doubles feature space, increases memory footprint

**9. Title Overweighting (8x)**
- **Decision**: In clustering, concatenate title 8 times before appending content (first 600 chars)
- **Rationale**: Titles are more discriminative for same-issue articles, body text has too many generic terms ("국회", "정부")
- **Tradeoff**: May under-cluster articles with misleading titles

**10. JSONL for Article Storage**
- **Decision**: One JSON object per line (newline-delimited JSON)
- **Rationale**: Supports streaming processing, easy to append, grep-friendly, human-readable
- **Tradeoff**: No schema enforcement, parsing errors harder to debug (no line numbers in standard JSON)

---

## 6. Absolute Rules

### Testing

**1. No Unit Tests Required (Research Project)**
- This is a research/demo project, not production software
- Validation happens via end-to-end pipeline runs and manual UI inspection
- If tests are added later, use `pytest` with fixtures for sample JSONL files

**2. Data Integrity Checks**
- ALWAYS check file existence before reading (`os.path.exists()`)
- ALWAYS handle empty JSONL files gracefully (skip empty lines, return empty DataFrame)
- ALWAYS validate cluster_id >= 0 before processing (exclude noise points labeled -1)

**3. Model Compatibility**
- Classifier MUST load safetensors/pkl/bin/pt files (auto-detect in `classifier.py`)
- Tokenizer MUST match BERT model base (`klue/bert-base` expected)
- If model file missing, provide clear error message pointing to Docker Hub image or model download instructions

### Git

**4. Never Commit Large Files**
- `models/political_classifier/model.safetensors` (460MB) → EXCLUDED in `.gitignore`
- `data/` directory contents → EXCLUDED (generated at runtime)
- `__pycache__/`, `*.pyc`, `.env` → EXCLUDED
- Use `.dockerignore` to exclude same files from Docker build context

**5. Commit Messages**
- Use Korean for commit messages (project is Korea-focused)
- Format: `<Component>: <Action> <Details>` (e.g., `Docker: Ollama 자동 초기화 추가`)
- No emoji in commits (keep professional)

**6. Branch Strategy**
- Single `main` branch (no feature branches for solo research project)
- Tag releases with `v1.0`, `v1.1` etc. when publishing to Docker Hub

### Coding Conventions

**7. Python Style**
- Follow PEP 8 (4-space indents, snake_case for functions/variables)
- Docstrings for all public functions (Google style)
- Type hints encouraged but not mandatory (legacy code has none)

**8. File Encoding**
- ALWAYS use `encoding='utf-8'` when reading/writing files (Korean text)
- NEVER assume default encoding (varies by OS)

**9. Error Handling**
- Wrap file I/O in try/except with informative error messages
- For pipeline steps, print step number and description before execution (`print("\n" + "="*70)`)
- NEVER silently swallow exceptions (at minimum, log stack trace with `traceback.print_exc()`)

**10. Environment Variables**
- REQUIRED: `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET` (crawling)
- OPTIONAL: `OLLAMA_BASE_URL`, `OLLAMA_MODEL` (defaults provided)
- Load via `python-dotenv` at module level, fallback to `os.getenv()` with defaults

**11. Logging**
- Use print statements for user-facing pipeline progress (simple, works in Docker logs)
- Use `tqdm` for progress bars in loops (batch processing, crawling)
- Reserve `logging` module for module-level debug info (currently only in crawler)

**12. Dependency Management**
- Pin major versions in `requirements.txt` (e.g., `torch>=2.0.0`)
- NEVER pin exact versions unless critical (e.g., `safetensors>=0.4.0` not `==0.4.1`)
- Document special install notes (PyTorch CUDA, Ollama binary) in README, not requirements.txt

**13. Docker Best Practices**
- Multi-stage builds NOT used (simplicity over size optimization)
- Use CPU-only PyTorch in Docker (CUDA adds ~2GB, not needed for inference)
- COPY requirements.txt before code (leverage layer caching)
- Use named volumes for persistent data (`ollama-data`)
- Health checks MUST be defined for all services

**14. UI Conventions (Streamlit)**
- Dark theme enforced via custom CSS (background `#0e1117`, text `#ffffff`)
- Stance badges color-coded: progressive=red `#FF6B6B`, conservative=blue `#45B7D1`, neutral=teal `#4ECDC4`
- ALWAYS escape user-generated content in `st.markdown(..., unsafe_allow_html=True)` (prevent XSS)
- Use `st.session_state` for selected_issue to persist selection across reruns

**15. Data Format Standards**
- JSONL files MUST have one object per line, no trailing commas
- JSON keys MUST match between pipeline steps: `cluster_id`, `cluster_label`, `political_stance`, `stance_confidence`
- Timestamps MUST be ISO 8601 strings (`published_at` field) or human-readable Korean (`pubDate` field)

---

## 7. Research Notes

### Current Research Questions

**1. Clustering Quality**
- How sensitive is HDBSCAN to min_cluster_size and min_samples?
- Can we use BERTopic or Top2Vec to improve topic coherence?
- What is the optimal title:content ratio for TF-IDF weighting?

**2. Classification Accuracy**
- How does model perform on neutral vs. clearly partisan articles?
- Can we use media outlet as a weak supervision signal (bootstrap training)?
- Should we add a 4th class for "non-political" articles (filter at classification step)?

**3. Summarization Quality**
- Is gemma2:2b sufficient for Korean political text, or should we upgrade to gemma2:9b?
- Can we use extractive summarization (TextRank) as a fallback when Ollama unavailable?
- How to evaluate summary quality (ROUGE, human evaluation)?

### Experiments to Run

**1. Ablation Study: Clustering Components**
- TF-IDF (word only) vs. TF-IDF (word + char) vs. Sentence-BERT embeddings
- UMAP n_components: 2 vs. 10 vs. 50 (for n_samples > 100)
- HDBSCAN min_cluster_size: 2 vs. 3 vs. 5

**2. Classifier Architecture Variants**
- Pure BERT (no TextCNN) as baseline
- BERT + TextCNN (no attention) as mid-tier
- Current BERT + TextCNN + Attention as full model
- Compare F1 scores on held-out test set

**3. Crawler Coverage Analysis**
- Compare balanced 11-outlet mode vs. all-sources mode: diversity, bias, topic distribution
- Measure redundancy: what % of articles are near-duplicates (title cosine similarity > 0.9)?

### Future Improvements

**1. Real-Time Monitoring**
- Add cron job or scheduler to run `pipeline.py --steps 1,3,4` every 6 hours
- Store historical data to track issue evolution over time
- Implement change detection (new clusters, shifting stances)

**2. Advanced NLP**
- Named Entity Recognition (NER) to extract politicians, parties, policies mentioned
- Sentiment analysis per stance (are conservative articles more negative than progressive on this issue?)
- Quote extraction (attribute statements to specific speakers)

**3. User Features**
- Bookmark/save issues
- Export summaries to PDF/Word
- Share issue link (requires persistent storage or URL encoding of cluster_id)
- User feedback on summary quality (thumbs up/down)

**4. Performance Optimization**
- Cache BERT embeddings for classification (avoid recomputing on re-runs)
- Parallelize Ollama summarization (run 4 prompts concurrently per cluster)
- Use SQLite for data storage (enable filtering/sorting without loading full JSONL)

**5. Evaluation Framework**
- Collect ground-truth labels for 100 articles (manual annotation)
- Compute precision/recall/F1 for classifier
- Compute cluster purity and normalized mutual information (NMI) for clusterer
- Human evaluation of summaries (coherence, accuracy, bias)

---

## Notes

- **GitHub Repository**: https://github.com/joon1216/issuefit_project (Public)
- Model file (`model.safetensors`) is 460MB and excluded from Git due to GitHub's 100MB file size limit. Use Docker Hub image `beakwol/issuefit:latest` for pre-packaged deployment, or download model separately.
- Ollama service requires ~4GB RAM and ~2GB disk for `gemma2:2b` model. First run downloads model automatically (1.6GB, takes 5-10 minutes).
- Streamlit UI reads files on every page load — not suitable for >10K articles without database backend.
- Clustering step (Step 2) is separate because it requires heavy computation and hyperparameter tuning — not included in default `--steps 1,3,4` workflow.
- If running on CPU, classification speed is ~5-10 articles/sec (batch_size=32). GPU (CUDA) achieves ~50-100 articles/sec.

---

## Session Log

### 2026-05-29
- **Task**: Initial GitHub repository setup and CLAUDE.md creation
- **Actions**:
  - Created comprehensive CLAUDE.md documentation (390 lines)
  - Updated remote URL from beakwol/issuefit_project to joon1216/issuefit_project
  - Verified .gitignore excludes model.safetensors (460MB) and .env (sensitive)
  - Pushed initial commit to GitHub
- **Result**: ✅ Success — Repository live at https://github.com/joon1216/issuefit_project

---

**Last Updated**: 2026-05-29  
**Version**: 1.0 (Local/Docker)  
**Maintainer**: joon1216 (rlawnsdudrlawnsdud1216@gmail.com)
