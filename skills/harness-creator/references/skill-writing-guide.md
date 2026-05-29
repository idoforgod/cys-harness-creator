> ⚠️ **구현 현황은 [`IMPLEMENTATION-STATUS.md`](IMPLEMENTATION-STATUS.md)가 우선한다.** 이 문서의 설계 서술 중 dispatch(dynamic)/supervisor·expert-pool·hierarchical 등은 M1-deferred(미구현)이며, `.claude/commands` 비우기 규칙은 폐기됐다.

# 스킬 & 스키마 작성 가이드 (CYS)

> 출처: 원본 `skill-writing-guide.md`을 CYS 패러다임으로 적응.

도메인 오케스트레이터 **SKILL.md**와 노드 **output_schema**(머신검증 JSON Schema)를 고품질로 저작하기 위한 상세 가이드. harness-creator 메타스킬 **Phase 3~4**의 보충 레퍼런스.

원본은 "스킬 본문이 곧 트리거이자 실행 지시서"라는 모델이었다. CYS에서는 **실행 지시는 `graph.json` → `workflow.js`(결정론 런타임)와 agent 파일이 담당**하고, 오케스트레이터 SKILL.md는 그 계약의 **사람용 진입점·트리거·뷰**가 된다. 따라서 원본의 트리거 설계·Why-First·Progressive Disclosure 지혜는 **그대로 보존**하되, "출력 형식 정의"는 산문 템플릿이 아니라 **머신검증 output_schema 설계**로 승격된다.

---

## 목차

1. [스킬의 두 종류: 상속받은 것 vs 저작하는 것](#1-스킬의-두-종류-상속받은-것-vs-저작하는-것)
2. [오케스트레이터 SKILL.md description 작성 패턴](#2-오케스트레이터-skillmd-description-작성-패턴)
3. [본문 작성 스타일 (Why-not-ALWAYS · 일반화 · 명령형 · 컨텍스트 절약)](#3-본문-작성-스타일)
4. [오케스트레이터 본문 구조 (graph.json의 사람용 뷰)](#4-오케스트레이터-본문-구조-graphjson의-사람용-뷰)
5. [output_schema 설계 (NEW — 머신검증 계약)](#5-output_schema-설계-new--머신검증-계약)
6. [Progressive Disclosure 패턴](#6-progressive-disclosure-패턴)
7. [agent 본문과 SKILL.md의 역할 분담 (중복 금지)](#7-agent-본문과-skillmd의-역할-분담-중복-금지)
8. [측정·평가 데이터 스키마 표준](#8-측정평가-데이터-스키마-표준)
9. [SKILL.md에 포함하지 않을 것](#9-skillmd에-포함하지-않을-것)
10. [진화·피드백 루프 (관찰 → 일반화)](#10-진화피드백-루프-관찰--일반화)

---

## 1. 스킬의 두 종류: 상속받은 것 vs 저작하는 것

CYS 하네스 안에는 두 부류의 스킬이 공존한다. 둘을 혼동하면 "이미 게놈이 주는 것"을 다시 쓰거나, "직접 써야 할 진입점"을 빠뜨린다.

| 구분 | 상속 스킬 (genome) | 도메인 오케스트레이터 스킬 (저작) |
|------|-------------------|--------------------------------|
| 출처 | `inherit_genome.py`가 게놈 228파일과 함께 복사 (`emit_workflow.py`가 자동 호출) | **메타스킬이 Phase 4에서 직접 작성** |
| 위치 | `.claude/skills/{workflow-generator, doctoral-writing, spec-grounded-workflow}/` | `.claude/skills/<domain>-orchestrator/SKILL.md` |
| 역할 | 자식 하네스의 일반 운영 능력(워크플로우 생성·학술 글쓰기 등) | **이 하네스 한 개**를 트리거·설명·실행하는 진입점 |
| 수정 | 손대지 않는다 (게놈 불변) | 이 가이드의 대상 — 도메인마다 새로 쓴다 |

> **핵심 원칙:** 자식 하네스는 게놈을 통째로 물려받아 이미 풍부한 운영 기계(컨텍스트 보존 hook, 4계층 품질 게이트, 보안 hook, 에이전트, 프롬프트 라이브러리)를 **갖고 태어난다**. 이 가이드와 메타스킬의 저작 작업은 **앞단(front-half) 설계** — 도메인을 `graph.json` + agent + schema + 오케스트레이터 SKILL.md로 옮기는 일 — 에 집중한다. 상속된 뒷단(back-half) 기계는 다시 만들지 않는다.

검증기는 이 구분을 안다: `validate_harness.py`의 DOC_DRIFT 체크는 `.claude/skills/` 아래에서 **이름이 `-orchestrator`로 끝나는 디렉토리만** 도메인 스킬로 인식하고 phase-count drift를 검사한다(상속 게놈 스킬은 무시). 따라서 저작하는 오케스트레이터 스킬 디렉토리는 **반드시 `<domain>-orchestrator` 규칙**을 지킨다.

---

## 2. 오케스트레이터 SKILL.md description 작성 패턴

`description`은 오케스트레이터 스킬의 **유일한 트리거 메커니즘**이다. Claude는 `available_skills` 목록에서 name + description만 보고 이 하네스를 실행할지 결정한다. 이 지혜는 원본에서 1:1로 가져온다.

### 트리거 메커니즘 이해 (원본 보존)

Claude는 자신의 기본 도구로 처리할 수 있는 단순 작업에는 스킬을 호출하지 않는 경향이 있다. "이거 한 번 검색해줘" 같은 요청은 description이 완벽해도 트리거되지 않을 수 있다. **복잡·다단계·전문적·재실행 가능한 작업일수록 트리거 확률이 높다** — 이것은 정확히 하네스가 존재해야 하는 조건(Phase -1 warrant가 `build-harness`를 내는 조건)과 일치한다. 즉 트리거가 잘 되는 description은 곧 "하네스가 정당화되는 상황"을 묘사한 것이다.

### 작성 원칙 (원본 보존 + CYS 추가)

1. **이 하네스가 하는 일** + **구체적 트리거 상황**을 모두 기술.
2. 유사하지만 트리거하면 안 되는 경계 조건 명시.
3. 약간 **pushy**하게 — Claude의 보수적 트리거 경향을 보상.
4. **(CYS 추가) 후속 작업을 description에 명시한다.** 재실행·수정·보완·부분 재생성·이전 결과 개선 요청도 이 스킬을 타야 한다. 하네스는 git repo이자 `resumeFromRunId`로 재개되는 자산이므로, "한 번 만들고 끝"이 아니라 "계속 돌리고 진화시키는" 대상이다. description이 후속을 안 잡으면 사용자는 두 번째 요청에서 하네스를 우회해 버린다.

### 좋은 예시 (deep-research 실제 오케스트레이터)

```yaml
description: "deep-research 하네스를 실행하는 오케스트레이터. 심층 리서치/조사/
  팩트체크 요청 시 사용. 후속: 리서치 재실행, 결과 업데이트, 보완, 다시 조사,
  이전 결과 개선 요청 시에도 반드시 이 스킬을 사용."
```

이 예시가 좋은 이유: (a) 하는 일(심층 리서치 실행)과 트리거 상황(리서치/조사/팩트체크)을 함께 명시, (b) "반드시 이 스킬을 사용"으로 pushy, (c) **후속 5종(재실행·업데이트·보완·다시 조사·개선)을 명시적으로 잡아** 두 번째 요청에서 우회를 막음.

### 좋은 예시 (다른 도메인 — 경계 조건까지)

```yaml
description: "ticket-triage 하네스 — 들어온 고객 티켓을 분류·우선순위화·라우팅한다.
  티켓/이슈/문의를 분류·트리아지·할당해야 할 때 사용. 단발 질문 답변이 아니라
  여러 티켓을 일관 기준으로 반복 처리할 때 특히 유용. 후속: 재트리아지, 기준 변경
  후 재실행, 누락 티켓 보완 시에도 이 스킬을 사용."
```

### 나쁜 예시 (원본 보존)

- `"데이터를 처리하는 스킬"` — 너무 모호. 어떤 도메인·작업인지 불분명, 트리거 안 됨.
- `"리서치 관련 작업"` — 구체적 동작·트리거 상황 미기술.
- `"graph.json을 실행한다"` — 내부 구현 노출. 사용자 언어가 아니라 트리거가 안 걸림. description은 **사용자가 쓰는 도메인 언어**로 쓴다(`graph.json`·`workflow.js` 같은 내부 용어는 본문에서만).

### 트리거 니어미스 검증 (원본 보존)

description을 쓴 뒤 **트리거 경계를 의심한다**: "이 도메인과 비슷하지만 하네스를 안 타야 하는 요청"을 3개 떠올려 description이 그것들을 흡수하지 않는지 확인하고, 반대로 "타야 하는데 표현이 살짝 다른 요청"(예: "조사" vs "리서치" vs "팩트체크") 3개를 흡수하는지 확인한다. 흡수 못 하면 동의어·후속 표현을 보강한다.

---

## 3. 본문 작성 스타일

### Why-not-ALWAYS 원칙 (원본 보존)

LLM은 **이유를 이해하면 엣지 케이스에서도 올바르게 판단**한다. `ALWAYS`/`NEVER` 같은 강압 규칙은 규칙이 닿지 않은 상황에서 무너진다. 맥락(왜)을 주면 일반화한다.

**나쁜 예:**
```markdown
ALWAYS run warrant.py before Workflow(). NEVER skip the cost band.
```

**좋은 예:**
```markdown
실행 전 `warrant.py --graph`로 토큰 비용 밴드를 표시하고 승인을 받는다.
budget.approval_required=true이고 budget.total이 런타임의 하드 ceiling이므로,
승인 없이 돌리면 사용자가 예상 못 한 토큰이 소모되고 ceiling 도달 시
파이프라인이 부분결과로 중단되기 때문이다.
```

> **주의 — CYS에서 "강압 규칙"의 자리는 산문이 아니라 게이트다.** 원본은 모든 규칙을 산문으로 설득해야 했다. CYS에서 진짜 불변(스키마 준수, 모델 티어, write-path 비중첩, 절대경로 금지 등)은 **`validate_harness.py`(머신체크 세트)와 `warrant.py`가 빌드/실행 게이트로 강제**한다. 따라서 SKILL.md 본문은 "Claude가 판단해야 하는 엣지"에만 Why를 쓰고, "기계가 막는 것"은 굳이 산문으로 반복하지 않는다(컨텍스트 절약). 산문으로 `ALWAYS write valid JSON`이라 쓰지 말고, 그건 `output_schema`가 강제하게 둔다.

### 일반화 원칙 (원본 보존)

피드백·테스트에서 문제가 발견되면 특정 예시 패치가 아니라 **원리 수준에서 일반화**한다.

**오버피팅 수정:**
```markdown
"Q4 매출" 티켓은 finance 큐로 보낸다.
```

**일반화된 수정:**
```markdown
티켓 본문에 금액·청구·환불 등 재무를 암시하는 키워드가 있으면 finance 큐로
라우팅한다. 모호하면 큐를 단정하지 말고 confidence를 낮춰 표기한다(다운스트림
합성 노드가 gap을 처리).
```

### 명령형 어조 (원본 보존)

"~합니다", "~할 수 있습니다" 대신 "~한다", "~하라". SKILL.md는 지시서다.

### 컨텍스트 절약 (원본 보존 + CYS 강화)

컨텍스트 윈도우는 공공재다. 모든 문장이 토큰 비용을 정당화하는지 자문한다:
- "Claude가 이미 아는 내용인가?" → 삭제
- "이 설명이 없으면 실수하는가?" → 유지
- "구체적 예시 하나가 긴 설명보다 효과적인가?" → 예시로 대체
- **(CYS) "이건 게이트·스키마·agent파일·README가 이미 강제/기술하는가?"** → 삭제(중복 SOT 금지). 오케스트레이터 SKILL.md는 **graph.json의 얇은 사람용 뷰**이지 두 번째 진실원천이 아니다.

---

## 4. 오케스트레이터 본문 구조 (graph.json의 사람용 뷰)

오케스트레이터 SKILL.md는 자유 산문이 아니라 **graph.json을 사람이 읽을 수 있게 투영한 정형 문서**다. 권장 골격(deep-research 실측 기반):

```markdown
# <Domain> Orchestrator (Mode A — Workflow 런타임)

`graph.json`의 사람용 뷰. 실제 실행은 `.harness/workflow.js`(emit 결과)를
`Workflow({scriptPath})`로 호출한다.

## 실행 모드: workflow (결정론 서브에이전트)   ← 또는 team (Mode B, 예외)

## 파이프라인 (N Phase)
| Phase | 노드 | 에이전트 | 모델 | 메커니즘 | 출력 |
| ...   | id   | agent    | tier | decision_mechanism | write_path |

## 실행
1. 컨텍스트 확인 (_workspace 존재 → 초기/재실행/부분재실행)
2. 입력 저장 경로
3. 비용 승인 — warrant.py --graph → 밴드 표시 → 승인 대기
4. 실행 — Workflow({ scriptPath, args }), budget.total = 하드 ceiling
5. 재개 — resumeFromRunId (변경 노드부터)

## 데이터 흐름  (한 줄 화살표 다이어그램)
## 에러 핸들링  (노드별 on_exhaust · 예산 초과 거동 · 빈 입력 degraded)
## 테스트 시나리오 (정상 1 + 에러 1)
```

규칙:
- **phase-count는 README와 일치해야 한다.** `validate_harness.py`의 DOC_DRIFT가 README와 오케스트레이터 SKILL.md의 phase 수가 다르면 잡는다(error/warn은 constants). 표의 Phase 행 수 = README가 말하는 단계 수.
- 표의 모델·메커니즘·출력 경로는 **graph.json에서 그대로 베껴온다**(손으로 다른 값을 쓰면 두 SOT 충돌). graph.json이 진실, 표는 뷰.
- **Mode A가 디폴트**임을 본문에 명시한다("결정론 서브에이전트 파이프라인. 에이전트 간 실시간 comms 없음"). Mode B(team)는 실시간 상호 통신이 필수일 때만이고, 그 경우 본문에 "이 하네스는 team(Mode B)이며 결정론 스케줄 불가 — 플랫폼 한계" 사실을 정직하게 적는다.
- 실행 명령은 **있는 그대로 복붙 가능**하게 적는다(추상적 설명 금지). `Workflow({ scriptPath: ".harness/workflow.js", args: {...} })`처럼 실제 호출형으로.

---

## 5. output_schema 설계 (NEW — 머신검증 계약)

원본의 "출력 형식 정의"는 산문 마크다운 템플릿(`# 제목 / ## 요약 / ...`)이었다. CYS에서 출력 형식은 **노드별 `output_schema` JSON Schema 파일**로 승격된다 — 이건 사람용 권고가 아니라 **런타임이 강제하는 계약**이다. `emit_workflow.py`가 각 `node.output_schema`를 로드해 `workflow.js` 안에 `const S = {...}` S-테이블로 인라인하고, `agent({ schema: S.<id>_schema })`로 서브에이전트 출력에 적용한다. 스키마를 어기는 출력은 파이프라인을 중단시킨다(원본의 "형식이 안 맞으면 사람이 알아채길 바람"과 차원이 다르다).

### 5.1 작성 위치와 참조

- 파일: `schemas/<name>.json` (하네스 루트 기준 상대경로). node.output_schema에 이 상대경로를 적는다.
- `reflect-then-revise` 노드는 critic 패스용 `schemas/critique.json`이 **추가로** 필요하다 — 메타스킬 SKILL.md Phase 3에 명시된 규칙. emitter는 convention으로 `schemas/critique.json`을 발견하면 `<id>_critique` 키로 인라인한다.
- `validate_harness.py`의 SCHEMA_FILE_EXISTS 체크가 node.output_schema가 가리키는 파일의 존재를 강제한다(없으면 emit·빌드 실패).

### 5.2 절대 규칙 (machine-enforced, 어기면 런타임 거부)

1. **`additionalProperties: false`** — 모든 object 레벨에 둔다(중첩 포함). 서브에이전트가 임의 필드를 끼워 넣어 다운스트림을 오염시키는 것을 막는다.
2. **`$schema`·`$id` 메타키는 인라인 시 제거된다.** emitter의 `_clean_schema()`가 최상위에서 두 키를 떼어낸 뒤 인라인한다. 이유는 경험적: Workflow 런타임의 `agent({schema})` 검증기는 `$schema: ".../draft/2020-12"`를 ref로 해석하려다 거부하고 `$id`도 거부한다.
   - **소스 schema 파일에는 둘을 적어도 된다**(에디터·외부 도구의 IDE 검증 편의; deep-research 실측 파일도 `$id: "findings.json"`를 가짐). emitter가 인라인 직전에 알아서 떼어낸다. 단 **bare-filename $id만** 쓴다(`"findings.json"` 같은). URL `$id`/`$schema`도 떼어지므로 무해하지만 bare-filename 관례를 따른다.
3. **`$ref` 금지.** 우리 스키마는 ref를 쓰지 않으므로 `_clean_schema()`는 최상위만 청소한다(중첩 청소 불필요). ref를 쓰면 인라인 후 해소 실패한다. 공유 구조가 필요하면 그냥 인라인 복제한다(단일 사용 추상화 금지 원칙과도 일치).
4. **`required`를 정직하게 명시.** 다운스트림이 의존하는 키는 required. 단, **빈 결과도 스키마는 유지**되게 설계한다(예: `claims: []`, `sources: []` 허용) — `on_exhaust: proceed-with-gap` 노드가 빈 배열로 degraded 진행할 수 있어야 하므로 배열 자체는 required지만 minItems는 두지 않는다.
5. **enum·min/max로 값 도메인을 좁힌다.** `severity: enum[low,med,high]`, `confidence: number min 0 max 1`. 자유 문자열보다 enum이 다운스트림 분기를 안전하게 한다.

### 5.3 스키마가 곧 노드 간 계약 (cross-comparison 가능)

스키마는 **노드 경계의 교차 비교 지점**이다(원본 QA 경계 cross-comparison 지혜의 CYS 구현). 한 노드의 output_schema 필드가 다음 노드의 입력·다음 스키마와 **상호 참조 가능한 안정 키**를 갖도록 설계하면, 적대적 리뷰·팩트체크 노드가 경계를 기계적으로 검증할 수 있다.

deep-research 실측 — `findings.json`이 만든 키를 `critique.json`이 참조하고 `report.json`이 다시 참조한다:

```json
// schemas/findings.json (gather/fetch/reviser 산출)
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",   // ← 인라인 시 제거됨
  "$id": "findings.json",                                       // ← bare-filename, 인라인 시 제거됨
  "type": "object", "additionalProperties": false,
  "required": ["claims", "sources"],
  "properties": {
    "claims": { "type": "array", "items": {
      "type": "object", "additionalProperties": false,
      "required": ["id", "text", "source_ids", "confidence"],
      "properties": {
        "id":         { "type": "string" },                     // ← critique가 claim_id로 참조
        "text":       { "type": "string" },
        "source_ids": { "type": "array", "items": { "type": "string" } },  // ← sources[].id로 해소
        "confidence": { "type": "number", "minimum": 0, "maximum": 1 }
      } } },
    "sources": { "type": "array", "items": {
      "type": "object", "additionalProperties": false,
      "required": ["id", "url", "title"],
      "properties": { "id": {"type":"string"}, "url": {"type":"string"}, "title": {"type":"string"} }
    } }
  }
}
```

```json
// schemas/critique.json (reflect-then-revise critic 산출)
{
  "type": "object", "additionalProperties": false,
  "required": ["approved", "issues"],
  "properties": {
    "approved": { "type": "boolean" },                          // ← true면 revise 루프 조기 종료
    "issues": { "type": "array", "items": {
      "type": "object", "additionalProperties": false,
      "required": ["claim_id", "problem", "severity"],
      "properties": {
        "claim_id": { "type": "string" },                       // ← findings claims[].id를 가리킴
        "problem":  { "type": "string" },
        "severity": { "type": "string", "enum": ["low", "med", "high"] }
      } } }
  }
}
```

설계 의도가 스키마에 박혀 있다: `critique.approved=true`는 reviser 루프를 조기 종료시키는 **제어 신호**이고, `issues[].claim_id`는 `findings.claims[].id`를 가리켜 **어떤 claim이 왜 문제인지**를 기계가 추적한다. 스키마 필드는 단순 데이터가 아니라 **메커니즘의 배선**이다 — 이걸 설계할 때 "다음 노드가 이 키로 무엇을 분기하는가"를 항상 함께 생각한다.

### 5.4 스키마 description은 토큰을 쓸 값어치가 있다

각 필드의 `description`은 서브에이전트가 무엇을 채워야 하는지 알려주는 인-밴드 지시다(스키마가 프롬프트와 함께 전달됨). "이 키가 어디서 참조되는지"를 적으면 모델이 안정 키를 일관되게 부여한다. 예: `"id": "Stable claim identifier, referenced by critique.issues[].claim_id."`. 단 컨텍스트 절약 원칙 적용 — 자명한 필드는 description 생략.

---

## 6. Progressive Disclosure 패턴

원본의 3패턴을 CYS 레이아웃으로 보존한다. **얇은 본문 + 깊은 references**가 핵심.

### 패턴 1: 도메인별 분리 (원본 보존)

오케스트레이터가 여러 하위 도메인을 다루면 references로 쪼갠다:

```
<domain>-orchestrator/
├── SKILL.md              (개요 + 노드 표 + 어떤 reference를 언제 읽나)
└── references/
    ├── routing-rules.md  (티켓 → 큐 분류 기준)
    └── escalation.md     (on_exhaust=escalate 시 사람 핸드오프 절차)
```

사용자가 라우팅을 물으면 `routing-rules.md`만 로드.

### 패턴 2: 조건부 상세 (원본 보존)

```markdown
## 실행
표준 실행은 위 5단계를 따른다.

**부분 재실행이 필요하면**(일부 노드만 갱신): [references/resume.md](references/resume.md)
**Mode B(team)로 마이그레이션해야 하면**: [references/mode-b-migration.md](references/mode-b-migration.md)
```

### 패턴 3: 대형 레퍼런스 파일 구조 (원본 보존)

150줄(원본은 300줄) 이상 reference 파일은 상단에 목차를 둔다. (이 파일이 그 예다.)

### CYS 추가: "다시 만들지 말 것"을 본문에 1줄 적시

자식 하네스는 게놈을 상속하므로 컨텍스트 보존·품질 게이트·보안 hook을 **이미 갖고 있다**. 오케스트레이터 본문에서 이 기능들을 다시 설명하면 토큰 낭비 + 두 번째 SOT가 된다. 필요하면 "상속된 게놈 기계는 `CLAUDE.md` §CYS Harness Engine / `.harness/RUNTIME.json` 참조" 한 줄로 가리키고 본문은 도메인 로직에만 쓴다.

---

## 7. agent 본문과 SKILL.md의 역할 분담 (중복 금지)

원본에서는 "스킬 본문"이 트리거 + 도메인 지식 + 실행 절차를 다 담았다. CYS는 **3원천으로 분산**되고, 각 원천이 자기 몫만 가진다(SOT 중복 금지):

| 정보 | 어디에 | 비고 |
|------|--------|------|
| 트리거(언제 이 하네스를) | 오케스트레이터 `description` | §2 |
| 단계·데이터흐름·실행/재개 명령(사람용 뷰) | 오케스트레이터 본문 | §4, graph.json의 투영 |
| **노드의 실제 작업 지시**(핵심역할·작업원칙·입출력 프로토콜·에러핸들링) | `.claude/agents/<agent>.md` 본문 | 서브에이전트가 읽는 실행 지시서 |
| 출력 형식(강제) | `schemas/*.json` | §5 |
| 단계 수 등 사실 | README ↔ 오케스트레이터(일치 강제) | DOC_DRIFT |

agent 파일 frontmatter에는 §model-tier 정책이 강제하는 필드가 들어간다(deep-research `researcher.md` 실측):

```yaml
---
name: researcher
description: Use FIRST for any deep-research request. ... 리서치, 조사, 검색. Pipeline stage 1.
tools: WebSearch, WebFetch, Read, Write      # least-privilege
model: haiku                                  # REQUIRED — node.model과 일치해야 함(V3)
model_rationale: "Pure web search + claim drafting, no cross-source judgment — cheapest tier."  # REQUIRED(M0=warn)
---
```

- **`model`과 `model_rationale`는 필수**다. `model`이 비거나 무효면 `validate_harness.py` V1이 error, agent frontmatter `model` ≠ node.model이면 V3가 error, pure-retrieval 역할(gather/extract/format/qa-scan)에 opus면 V2가 error(`tier_override_reason` 있으면 warn). role→tier 매핑: gather/extract/format/qa-scan=haiku, voter/debater/reviser=sonnet, synthesis/judge/critic/architecture=opus.
- **agent 본문에서 출력 프로토콜은 schema와 일치**시킨다. researcher 본문이 `schemas/findings.json 스키마로 JSON 반환` + 예시 JSON을 보여주듯, agent 본문의 예시가 schema와 어긋나면 모델이 헷갈린다. schema가 진실, 본문 예시는 그것의 미리보기.
- **에러핸들링은 on_exhaust와 정합**시킨다. `on_exhaust=proceed-with-gap` 노드의 agent 본문은 "빈 배열로 스키마는 유지"를 지시한다(§5.2 규칙4).

오케스트레이터 SKILL.md에 노드의 작업 지시를 다시 쓰지 않는다 — 그건 agent 파일의 몫이다.

---

## 8. 측정·평가 데이터 스키마 표준

스킬/하네스의 테스트·헤드투헤드 측정에 쓰는 표준 스키마(원본 보존 + CYS 도구 연결). CYS에서 측정은 산문 주장이 아니라 **`lift_gate.py`(with-skill vs haiku baseline, 독립 블라인드 그레이더 → register/refuse)와 `h2h_suite`/`h2h_aggregate`(n-run median 헤드투헤드)**가 수행한다 — 원본의 "with-skill vs without A/B 규율"의 기계화.

### eval_metadata.json (원본 보존)

```json
{
  "eval_id": 0,
  "eval_name": "descriptive-name-here",
  "prompt": "사용자의 작업 프롬프트",
  "assertions": ["산출물에 X가 포함되어 있다", "Y 형식으로 파일이 생성되었다"]
}
```

### grading.json (원본 보존 — 필드명 엄격)

```json
{
  "expectations": [
    { "text": "산출물에 '서울'이 포함됨", "passed": true,
      "evidence": "3번째 단계에서 '서울 지역 데이터 추출' 확인" }
  ],
  "summary": { "passed": 2, "failed": 1, "total": 3, "pass_rate": 0.67 }
}
```

**필드명 주의:** `text`, `passed`, `evidence`를 정확히 사용한다(`name`/`met`/`details` 변형 금지). lift_gate/h2h 그레이더가 이 필드명을 파싱한다.

### timing.json (원본 보존 + CYS budget 연결)

```json
{ "total_tokens": 84852, "duration_ms": 23332, "total_duration_seconds": 23.3 }
```

서브에이전트 완료 알림에서 `total_tokens`·`duration_ms`를 **즉시 저장**한다 — 알림 시점에만 접근 가능, 이후 복구 불가. CYS에서 `total_tokens`는 `budget.total_tokens`(하드 ceiling)와 warrant 비용밴드 사후 검증에 직접 쓰이므로 더 중요하다. (단, 결정론 런타임 자체는 wall-clock/RNG를 쓰지 않는다 — duration은 관측용 메타, 제어 신호 아님.)

---

## 9. SKILL.md에 포함하지 않을 것

- README.md·CHANGELOG.md·INSTALLATION_GUIDE.md 등 부가 문서 (오케스트레이터 SKILL.md 자체에 녹이지 않는다)
- 스킬/하네스 생성 과정의 메타 정보(테스트 결과, 반복 이력, 어느 워런트 판정이 나왔는지)
- 사용자 대상 설명서 — SKILL.md는 AI 에이전트용 지시서다(사람용은 README)
- 이미 Claude가 아는 일반 지식
- **(CYS) 게놈이 이미 주는 것의 재설명** — 컨텍스트 보존 hook·품질 게이트·보안·prompt-runner 동작을 본문에 베끼지 않는다(§6 마지막)
- **(CYS) graph.json의 두 번째 사본** — 표는 graph.json의 뷰일 뿐, node 정의·예산·메커니즘 파라미터의 원천이 되려 하지 않는다
- **(CYS) agent 작업 지시의 중복** — 노드의 핵심역할·작업원칙은 agent 파일에만(§7)
- **(CYS) `.claude/commands/`** — 게놈이 commands(install·maintenance 등)를 정당하게 상속하므로 비워둘 필요 없다(원본 NO_COMMANDS 규칙은 폐기). 오케스트레이터는 슬래시 커맨드가 아니라 description 트리거 + Workflow 호출로 동작하며, **새 도메인 커맨드를 직접 만들지는 않는다**

---

## 10. 진화·피드백 루프 (관찰 → 일반화)

원본의 진화 루프 + 스크립트 번들링 판단 지혜를 CYS로 적응한다. 헤드투헤드/lift 측정과 실제 실행 트랜스크립트를 **관찰**해서 스킬·스키마·agent를 개선한다.

| 관찰 신호 (트랜스크립트/h2h에서) | CYS 조치 |
|------|------|
| 서브에이전트가 매번 같은 형식 실수를 함 | output_schema에 enum/required/`additionalProperties:false` 보강 (산문 경고 추가 아님) |
| 트리거가 안 걸린 near-miss 요청 발견 | 오케스트레이터 description에 동의어·후속 표현 추가 (§2) |
| 한 노드가 만성적으로 retry 소진 | on_exhaust 재검토 + 그 노드의 model 티어/메커니즘 재검토 (예: single → reflect-then-revise) |
| 두 노드 경계에서 키 불일치로 다운스트림 깨짐 | 두 schema의 cross-reference 키를 정렬 (§5.3) |
| 비용밴드가 예산을 자주 초과 | pure-retrieval 노드 opus → haiku 강등, fan-out n 축소, budget.total 재산정 |
| 같은 도메인 지식을 매 실행에서 재발견 | agent 본문의 작업원칙으로 표준화 (단발 추측 기능 추가는 금지 — 단순성 우선) |

**일반화 규율(원본 보존):** 한 테스트 케이스를 고치려고 좁은 패치를 박지 않는다. 원리 수준으로 올려 스키마·티어 정책·description 동의어 같은 **구조에 반영**한다. 그래야 다음 하네스에도 전이된다.

**번들링 대신 게놈·스키마(원본 적응):** 원본은 반복 헬퍼를 `scripts/`에 번들했다. CYS에서 반복 절차는 대개 (a) 이미 게놈이 제공(중복 금지) 하거나 (b) output_schema/agent 작업원칙으로 표준화하면 사라진다. 정말 도메인 고유의 결정론 헬퍼가 필요하면 graph 외부 스크립트가 아니라 **agent의 tools**(least-privilege)나 **노드 메커니즘**으로 표현할 수 있는지 먼저 본다.

**검증 후 진화:** 어떤 변경도 `validate_harness.py` PASS(머신체크 세트) → `warrant.py` 비용밴드 승인 → 헤드투헤드 재측정의 순서를 다시 통과해야 등록된다. 정직 미달(baseline을 못 이김)이면 `lift_gate`가 refuse하고, 그 사실을 사용자에게 정직하게 보고한다(원본의 A/B 정직성 규율의 기계화).
