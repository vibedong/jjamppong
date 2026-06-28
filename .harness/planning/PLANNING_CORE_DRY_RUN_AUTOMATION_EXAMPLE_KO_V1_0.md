# Planning Core Dry Run: "자동화가 필요해"

artifact_id: harness.planning_core_dry_run_automation_example
artifact_version: 1.0

## 입력

```text
자동화가 필요해
```

## 기대 흐름

### 1. 요구사항화 금지 선언

아직 "자동화"를 요구사항, PRD, 개발 플랜, 제품 코드로 해석하지 않는다. 먼저 사용자가 말한 자동화의 의미와 금지 해석을 확인한다.

### 2. "자동화" 가능한 의미 제시

- 반복 실행
- 문서 정리
- AI 초안 제안
- 사람이 승인한 뒤 실행
- AI가 결정을 대신함
- 완전 무인 실행
- 오프라인 파일 처리
- 온라인 서비스 연동
- 검토 자동화
- 알림 또는 스케줄 실행

### 3. 모호성 장부 후보

```json
{
  "ambiguity_id": "AMB-001",
  "source_phrase": "자동화",
  "possible_meanings": [
    "반복 실행",
    "문서 정리",
    "AI 초안 제안",
    "사람 승인 후 실행",
    "AI 결정 대행",
    "완전 무인 실행"
  ],
  "chosen_meaning": [],
  "rejected_meanings": [],
  "status": "open",
  "blocks_next_stage": true,
  "creator_confirmation": false
}
```

### 4. 도메인 사전 후보

```json
{
  "term_id": "TERM-001",
  "term": "자동화",
  "definition": "",
  "examples": [],
  "counterexamples": [],
  "forbidden_interpretations": [],
  "confirmed_by_creator": false
}
```

### 5. 질문 대기열 후보

```json
{
  "question_id": "Q-001",
  "question_text": "당신이 말한 자동화는 위 의미 중 어디에 가깝나요? 그리고 절대 원하지 않는 자동화는 무엇인가요?",
  "purpose": "자동화의 chosen_meaning과 rejected_meanings를 분리한다.",
  "target_ambiguity": "AMB-001",
  "target_domain_term": "TERM-001",
  "priority": "blocking",
  "answer_status": "unasked",
  "blocks_completion": true
}
```

### 6. Decision Ledger 미기록

사용자가 아직 명확한 의미를 선택하지 않은 상태에서는 Decision Ledger에 기록하지 않는다.

Decision Ledger는 사용자가 특정 의미, 규칙, 범위를 명확히 확인한 뒤에만 갱신된다.

"자동화가 필요해" 첫 턴에서는 Ambiguity Ledger 후보, Domain Dictionary 후보, Question Queue 후보까지만 만든다.

### 7. 파일 쓰기 전 approval 필요

Ambiguity Ledger, Domain Dictionary, Question Queue, Decision Ledger, RunRecord 같은 실제 산출물 파일은 File Write Gate가 exact write paths를 승인하기 전까지 쓰지 않는다.

### 8. 제품 코드 생성 없음

이 dry run은 Planning Core discovery 흐름만 보여준다. 제품 코드, scaffold, validator, TDD, Superpowers 실행은 하지 않는다.
