# Harness Planning Core Product Specification v1.0

## 0. 한 문장 정의

Harness Planning Core는 비개발자인 사용자가 모호한 제품 아이디어를 말하면, AI가 소크라테스식 질문과 DDD 기반 도메인 발견을 통해 **공유 도메인 사전, 모호성 장부, 문제 정의, 목표, 규칙, non-goal, 결정 기록이 포함된 완전 기획안**으로 끌어내는 프로젝트 로컬 기획 엔진이다.

## 1. 왜 필요한가

기존 Harness 설계는 검토, 승인, 해시, 구현 관문, Work Unit 구조가 강했다. 그러나 사용자가 가장 중요하게 여기는 지점은 구현 통제보다 앞선다.

사용자의 핵심 문제는 다음이다.

- 사용자는 자기 머릿속에 있는 목표를 완전히 말로 표현하지 못한다.
- AI는 사용자가 말한 단어를 너무 빨리 요구사항으로 해석한다.
- “자동화”, “정리”, “기획”, “검토”, “완료” 같은 단어는 사람마다 의미가 다르다.
- 이 모호성이 해소되지 않으면 개발 에이전트는 나중에 임의 결정을 만들게 된다.
- 개발 후 수정에 쓰는 토큰과 비용은 기획 질문에 쓰는 비용보다 훨씬 크다.

따라서 Harness는 먼저 기획 단계에서 다음을 해야 한다.

```text
사용자 말
→ 핵심 단어 추출
→ 가능한 의미 폭발
→ 질문 압박
→ 도메인 사전
→ 모호성 장부
→ 규칙과 예외
→ non-goal
→ 결정 기록
→ 완전 기획안
```

## 2. 핵심 원칙

### 2.1 100% mind reading은 목표가 아니다

사용자의 머릿속을 100% 읽는 것은 불가능하다.

목표는 다음이다.

> 다음 단계의 AI가 중요한 제품 의미를 임의로 만들 필요가 없을 정도로 90% 이상 명확한 상태.

### 2.2 질문 수는 제한하지 않는다

질문은 5개일 수도 있고 100개일 수도 있다.  
중요한 것은 질문 수가 아니라 각 질문이 어떤 모호성을 줄이는가다.

### 2.3 공유 도메인 사전은 핵심 source of truth다

사용자와 AI는 같은 도메인 사전을 본다.  
기획, 스펙, 개발 플랜, Work Unit, 검토는 모두 이 사전을 참조한다.

### 2.4 모호성 장부가 없으면 기획이 아니다

모호한 표현은 대화 속에 흘려보내지 않는다.  
`AMB-###` ID로 기록하고 상태를 가진다.

### 2.5 grill-me는 질문 압박 능력이다

Matt Pocock 계열 grill-me는 “질문을 많이 하는 능력”으로 사용한다.  
Harness는 질문의 목적, 상태, 결과 변환, 완료 판정을 소유한다.

### 2.6 gstack은 기획 완료 전 검토자다

gstack 계열은 source artifact를 수정하지 않고, findings-only로 다음을 본다.

- 문제와 해결책 혼합
- 용어 모호성
- non-goal 부재
- 범위 과대·과소
- AI가 사용자 결정을 대신한 부분

### 2.7 Superpowers는 기획 단계에서 사용하지 않는다

Superpowers는 행동 스펙과 개발 플랜 이후 개발 단계에서 사용한다.

## 3. 전체 기획 시나리오

### P0. 아이디어 입력

사용자 입력 예시:

```text
자동화가 필요해.
```

AI 첫 응답:

```text
아직 “자동화”를 요구사항으로 해석하지 않겠습니다.
자동화는 여러 뜻을 가질 수 있습니다.
먼저 이 단어가 당신에게 정확히 무엇을 뜻하는지 확인하겠습니다.
```

산출:

- Raw Idea Record
- Initial Ambiguity Candidates

통과 조건:

- 핵심 단어가 추출됨

### P1. 요구사항화 금지 선언

목적:

- AI가 바로 PRD, 기능 목록, 개발 계획을 만들지 않도록 방지

사용자에게 보여줄 문장:

```text
지금은 요구사항을 확정하는 단계가 아닙니다.
먼저 문제, 사용자, 도메인 용어, 규칙을 확인합니다.
```

산출:

- Planning Session Mode = discovery

### P2. 핵심 단어 추출

예:

- 자동화
- 기획
- 검토
- 승인
- 정리
- 완료
- AI가 알아서

산출:

- Term Candidate List

통과 조건:

- 위험 단어가 Ambiguity Ledger로 등록됨

### P3. 핵심 단어 의미 폭발

“자동화” 예시:

- 반복 실행
- 초안 생성
- 질문 생성
- 정리
- 추천
- 결정 대행
- 무인 실행
- 승인 후 실행

질문:

```text
당신이 말한 자동화는 어디에 가깝나요?
그리고 절대 원하지 않는 자동화는 무엇인가요?
```

산출:

- Ambiguity Ledger row update

### P4. 사실·가정·해결책 후보·결정 분리

사용자 답변을 다음으로 분리한다.

- fact
- assumption
- proposed_solution
- decision
- open_question

통과 조건:

- 사용자 결정과 AI 제안이 섞이지 않음

### P5. 문제와 해결책 분리

질문:

```text
자동화가 해결책이라고 가정하지 않고 보겠습니다.
자동화가 없어서 실제로 어떤 문제가 생기나요?
```

검사:

- “자동화”가 problem인지 solution인지 분리됨

### P6. 실제 경험 이야기 수집

질문:

```text
마지막으로 이 문제가 실제로 발생했던 순간을 말해주세요.
언제였고, 무엇을 하려 했고, 어디서 막혔나요?
```

산출:

- Story Record
- Opportunity Candidate

### P7. 사용자·상황·고통 정의

기록:

- user role
- context
- trigger
- pain
- current workaround
- consequence

통과 조건:

- “누가 언제 왜 어려운가”가 문장으로 기록됨

### P8. 목표 후보 생성

AI는 하나의 목표를 바로 확정하지 않고 후보를 만든다.

예:

- 반복 작업 제거
- 기획 모호성 제거
- 개발 에이전트 통제
- 승인·검토 추적

사용자는 선택·수정한다.

### P9. 목표 후보 검증

검사 질문:

- 이 목표가 맞다면 무엇을 하지 않아야 하는가?
- 이 목표가 틀렸다면 어떤 단어가 틀렸는가?
- 이 목표를 달성했음을 어떻게 알 수 있는가?

### P10. 도메인 용어 추출

용어 후보:

- 아이디어
- 문제
- 목표
- 사용자
- 도메인
- 기획
- 검토
- 승인
- 스펙
- 작업 단위
- 구현
- 피드백
- 복귀

### P11. 도메인 사전 작성

각 term에는 다음을 기록한다.

- definition
- examples
- counterexamples
- forbidden interpretations
- related events
- related commands
- confirmed_by_creator

### P12. 도메인 사건 발견

사건 예시:

- 아이디어가 입력됨
- 모호한 단어가 발견됨
- 단어 의미가 확정됨
- 문제가 정의됨
- 규칙이 발견됨
- non-goal이 확정됨
- 기획 완료가 요청됨

### P13. Command 후보 발견

Command 예시:

- 아이디어 등록 요청
- 용어 정의 요청
- 문제 정의 확인 요청
- non-goal 추가 요청
- 기획 검토 요청
- 기획 완료 요청

### P14. 규칙·예외·불변조건 발견

예:

- 핵심 용어가 정의되지 않으면 다음 단계로 가지 않는다.
- AI 제안은 사용자 결정이 아니다.
- 검토 통과는 승인과 다르다.
- 자동화는 초안 생성까지 가능하지만 최종 승인 대행은 금지다.

### P15. 만들 것·만들지 않을 것

Shape Up의 no-go와 rabbit hole 개념을 반영한다.

- 만들 것
- 만들지 않을 것
- 위험한 rabbit hole
- 나중에 할 것
- 1.0에서 절대 제외할 것

### P16. 모호성 장부 정리

모든 ambiguity는 다음 중 하나여야 한다.

- clarified
- rejected
- deferred_non_blocking
- blocking

blocking이 남으면 다음 단계로 가지 않는다.

### P17. gstack findings-only 검토

검토 항목:

- 문제·해결책 혼합
- 목표 과대
- 용어 모호
- non-goal 부족
- AI 결정 대행
- 위험한 자동화

### P18. 완전 기획안 생성

산출물:

- Domain Planning Brief

### P19. 기획 완료 판정

완료 조건:

- 핵심 목표 확인
- 사용자·상황 확인
- 위험 단어 정의
- 도메인 사전 존재
- 모호성 장부 blocking 0
- 실제 이야기 존재
- 문제와 해결책 분리
- 규칙·예외·non-goal 존재
- 사용자 의미 확인

## 4. 핵심 artifact

### 4.1 Ambiguity Ledger

모호한 표현을 관리한다.

예:

```json
{
  "ambiguity_id": "AMB-001",
  "source_phrase": "자동화",
  "possible_meanings": ["반복 실행", "초안 생성", "AI 결정", "무인 실행"],
  "chosen_meaning": ["질문 생성", "답변 정리", "기획 후보 제안"],
  "rejected_meanings": ["AI 최종 승인", "무인 실행"],
  "blocks_next_stage": false,
  "creator_confirmation": true
}
```

### 4.2 Domain Dictionary

공유 도메인 사전이다.

예:

```json
{
  "term": "자동화",
  "definition": "AI가 질문, 정리, 기획 후보를 생성하지만 사용자의 제품 의미와 승인 판단을 대신하지 않는 것",
  "examples": ["AI가 문제 정의 질문을 생성한다"],
  "counterexamples": ["AI가 사용자 승인 없이 개발 작업을 만든다"],
  "confirmed_by_creator": true
}
```

### 4.3 Question Queue

질문의 목적과 상태를 추적한다.

### 4.4 Decision Ledger

사용자가 명확히 결정한 것만 기록한다.

### 4.5 Planning Brief

다음 단계로 넘길 완전 기획안이다.

## 5. 질문 종료 조건

질문은 다음 경우에만 멈춘다.

- blocking ambiguity가 0이다.
- 핵심 목표가 사용자에게 확인됐다.
- 핵심 용어가 도메인 사전에 있다.
- 문제와 해결책이 분리됐다.
- non-goal이 있다.
- 위험 단어의 금지 해석이 있다.
- 다음 단계 AI가 제품 의미를 새로 만들 필요가 없다.

## 6. 개발계획으로 넘길 조건

Planning Core의 output은 Development Plan이 아니라, 이후 Product Scope·Behavior Spec·Development Plan의 입력이다.

넘길 수 있는 상태:

```yaml
planning_core_status: complete
blocking_ambiguity: 0
domain_dictionary_confirmed: true
problem_solution_separated: true
non_goals_present: true
creator_meaning_confirmed: true
```

## 7. acceptance criteria

- 사용자가 “자동화” 같은 모호한 단어를 말하면 가능한 의미를 펼친다.
- AI는 바로 요구사항으로 변환하지 않는다.
- 모든 위험 단어는 Ambiguity Ledger에 기록된다.
- 모든 핵심 용어는 Domain Dictionary에 기록된다.
- 답변은 fact/assumption/proposed_solution/decision으로 분리된다.
- grill-style 질문은 Question Queue와 연결된다.
- gstack 검토는 findings-only로만 작동한다.
- Superpowers는 기획 단계에서 사용되지 않는다.
- 기획 완료 전 PRD, Behavior Spec, Development Plan, Work Unit을 만들지 않는다.
