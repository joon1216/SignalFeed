# 클러스터링/분류 입력용 JSONL 템플릿

## 파일 형식 설명

분류 테스트를 위한 JSONL 파일입니다. 하나의 주제로만 구성된 기사들을 작성하면 됩니다.

## 필드 설명

### 필수 필드
- `title`: 기사 제목 (문자열)
- `content`: 기사 본문 내용 (문자열)
- `cluster_id`: 클러스터 ID (숫자, 같은 주제면 모두 같은 값)
- `cluster_label`: 클러스터 레이블/주제명 (문자열, 같은 주제면 모두 같은 값)

### 선택 필드
- `url`: 기사 원본 URL (문자열 또는 null)
- `published_at`: 발행 시간 (문자열 또는 null)
- `thumbnail`: 썸네일 이미지 URL (문자열 또는 null)

## 예시

```json
{"title": "기사 제목", "content": "기사 본문 내용...", "url": "https://example.com/news", "published_at": "Tue, 30 Dec 2025 17:20:00 +0900", "thumbnail": null, "cluster_id": 0, "cluster_label": "테스트 주제"}
```

## 작성 방법

1. `clustering_template.jsonl` 파일을 복사하여 새 파일을 만듭니다
2. 각 라인에 하나의 기사 정보를 JSON 형식으로 작성합니다
3. **같은 주제의 기사들은 모두 같은 `cluster_id`와 `cluster_label`을 사용하세요**
4. 각 라인은 독립적인 완전한 JSON 객체여야 합니다 (쉼표로 구분하지 않음)
5. 마지막 라인 뒤에도 개행 문자를 넣어주세요

## 주의사항

- **분류 결과는 포함하지 마세요**: `political_stance`, `stance_confidence` 필드는 제거하세요
- JSON 형식이 올바른지 확인하세요 (쉼표, 따옴표 등)
- 파일 인코딩은 UTF-8입니다
- 각 라인은 줄바꿈 문자(`\n`)로 구분됩니다
- 이 파일을 분류기에 넣으면 `political_stance`와 `stance_confidence` 필드가 추가된 결과가 나옵니다

## 사용 예시

같은 주제로 여러 기사를 작성할 때:

```json
{"title": "기사 1", "content": "...", "cluster_id": 0, "cluster_label": "AI 정책", ...}
{"title": "기사 2", "content": "...", "cluster_id": 0, "cluster_label": "AI 정책", ...}
{"title": "기사 3", "content": "...", "cluster_id": 0, "cluster_label": "AI 정책", ...}
```

모두 같은 `cluster_id: 0`과 `cluster_label: "AI 정책"`을 사용하면 됩니다.
