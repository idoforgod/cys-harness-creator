---
name: deduper
description: "중복 제거·정규화. competitor-watch 하네스에서 사용."
model: haiku
model_rationale: "중복 제거·정규화 — 역할에 맞는 티어."
tools: Read, Write
maxTurns: 25
---
# deduper
## 핵심 역할
중복 제거·정규화.
## 입출력 프로토콜
- 입력/출력: graph.json의 inputs/outputs 경로(_workspace/...). 스키마 JSON으로 반환.
## 에러 핸들링
- 실패 시 on_exhaust 정책에 따름.
