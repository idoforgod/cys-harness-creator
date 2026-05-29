---
name: competitor-watch-orchestrator
description: "경쟁사 주간 모니터링 하네스 오케스트레이터. 경쟁사 뉴스 수집·요약 요청, 재실행·업데이트 시 사용."
---
# Competitor Watch Orchestrator (Mode A)
## 파이프라인 (3 Phase)
| Phase | 노드 | 에이전트 | 모델 |
|------|------|---------|------|
| Phase 1 | gather | scout | haiku |
| Phase 2 | dedupe | deduper | haiku |
| Phase 3 | brief | briefer | opus |
## 실행
warrant 비용승인 → `Workflow({scriptPath:".harness/workflow.js", args:{targets}})`.
