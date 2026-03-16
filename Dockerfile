# IssueFit - 정치 뉴스 분석 시스템
# Python 3.10 슬림 이미지 사용 (경량화)
FROM python:3.10-slim

WORKDIR /app

# 네이티브 패키지 빌드에 필요한 시스템 의존성 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    curl \
    libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*

# requirements.txt 먼저 복사 (레이어 캐시 최적화)
COPY requirements.txt .

# PyTorch CPU 전용 먼저 설치 (CUDA 버전 ~2GB → CPU 버전 ~700MB)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# 나머지 Python 의존성 설치
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 및 모델 복사
COPY app.py pipeline.py ./
COPY modules/ ./modules/
COPY models/ ./models/

# data/ 디렉토리는 docker-compose 볼륨으로 마운트됨
# (파이프라인 출력 파일이 호스트와 공유됨)

# Streamlit 포트
EXPOSE 8501

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -sf http://localhost:8501/_stcore/health || exit 1

# Streamlit 앱 실행
CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
