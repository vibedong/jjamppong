# Planning Core Runtime Schemas v1.0

## 1. AMBIGUITY_LEDGER_SCHEMA_V1_0.json

```json
{
  "ambiguity_id": "AMB-000",
  "source_phrase": "",
  "source_turn_id": "",
  "possible_meanings": [],
  "chosen_meaning": [],
  "rejected_meanings": [],
  "related_questions": [],
  "related_domain_terms": [],
  "related_rules": [],
  "risk_level": "low|medium|high|critical",
  "blocks_next_stage": true,
  "status": "open|asked|clarified|rejected|deferred_non_blocking|blocking",
  "creator_confirmation": false,
  "evidence": []
}
```

## 2. DOMAIN_DICTIONARY_SCHEMA_V1_0.json

```json
{
  "term_id": "TERM-000",
  "term": "",
  "definition": "",
  "examples": [],
  "counterexamples": [],
  "forbidden_interpretations": [],
  "related_events": [],
  "related_commands": [],
  "related_rules": [],
  "owner": "creator|harness|external_user|system",
  "confirmed_by_creator": false,
  "version": "1.0"
}
```

## 3. QUESTION_QUEUE_SCHEMA_V1_0.json

```json
{
  "question_id": "Q-000",
  "question_text": "",
  "purpose": "",
  "target_ambiguity": "",
  "target_domain_term": "",
  "priority": "blocking|high|normal|later",
  "stage": "P0-P19",
  "asked_count": 0,
  "answer_status": "unasked|asked|answered|clarified|deferred",
  "converted_to": [],
  "blocks_completion": true,
  "fatigue_risk": "low|medium|high"
}
```

## 4. DECISION_LEDGER_ENTRY_SCHEMA_V1_0.json

```json
{
  "decision_id": "DEC-000",
  "decision_text": "",
  "decision_type": "goal|scope|non_goal|term|rule|exception|workflow",
  "source_turn_id": "",
  "creator_confirmed": true,
  "ai_suggested": false,
  "basis": [],
  "supersedes": [],
  "status": "active|superseded|revoked"
}
```

## 5. PLANNING_RUN_RECORD_SCHEMA_V1_0.json

```json
{
  "run_id": "",
  "started_at": "",
  "stage": "",
  "persona": "socratic_domain_planner",
  "skill_family": "mattpocock|harness_native|gstack",
  "skill_used": "",
  "fallback_used": false,
  "input_artifacts": [],
  "output_artifacts": [],
  "question_count": 0,
  "blocking_ambiguity_before": 0,
  "blocking_ambiguity_after": 0,
  "creator_confirmations": [],
  "status": "completed|blocked|needs_user_answer"
}
```

## 6. PLANNING_COMPLETENESS_CHECK_V1_0

```yaml
goal_confirmed: true|false
target_user_confirmed: true|false
situation_confirmed: true|false
core_domain_terms_confirmed: true|false
risky_terms_have_forbidden_interpretations: true|false
story_record_present: true|false
problem_solution_separated: true|false
domain_events_present: true|false
rules_and_exceptions_present: true|false
non_goals_present: true|false
blocking_ambiguity_count: number
creator_meaning_confirmed: true|false
ready_for_product_scope: true|false
```
