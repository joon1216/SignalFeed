# 분류기 입력용 JSONL 파일 생성 가이드

## 파일 형식 설명

분류기에 넣을 입력 데이터용 JSONL 파일입니다. 각 라인마다 하나의 JSON 객체가 들어갑니다.

**중요**: 이 파일에는 분류 결과(`political_stance`, `stance_confidence`)가 포함되어 있으면 안 됩니다. 분류기를 돌려서 결과를 얻기 위한 **입력** 데이터입니다.

## 필수 필드

- `title`: 기사 제목 (문자열)
- `content`: 기사 본문 내용 (문자열)

## 선택 필드

- `url`: 기사 원본 URL (문자열 또는 null)
- `published_at`: 발행 시간 (문자열 또는 null)
- `thumbnail`: 썸네일 이미지 URL (문자열 또는 null)

## 예시

```json
{"title": "기사 제목", "content": "기사 본문 내용...", "url": "https://example.com/news", "published_at": "Tue, 30 Dec 2025 17:20:00 +0900", "thumbnail": null}
```

## 작성 방법

1. `classification_template.jsonl` 파일을 복사하여 새 파일을 만듭니다
2. 각 라인에 하나의 기사 정보를 JSON 형식으로 작성합니다
3. 각 라인은 독립적인 완전한 JSON 객체여야 합니다 (쉼표로 구분하지 않음)
4. 마지막 라인 뒤에도 개행 문자를 넣어주세요

## 주의사항

- **포함하지 말아야 할 필드**:
  - `cluster_id`, `cluster_label` (클러스터 정보)
  - `political_stance`, `stance_confidence` (분류 결과 - 아직 없어야 함)
- JSON 형식이 올바른지 확인하세요 (쉼표, 따옴표 등)
- 파일 인코딩은 UTF-8입니다
- 각 라인은 줄바꿈 문자(`\n`)로 구분됩니다
- 이 파일을 분류기에 넣으면 `political_stance`와 `stance_confidence` 필드가 추가된 결과가 나옵니다
