# CYS Harness Creator — M0 설계 명세서 (구현 준비 완료판)

> 작성: 마스터 클로드 · 2026-05-29 · 상태: **코딩 가능(비평가 8 must-fix + 과설계 scope-cut 반영)**
> 기반: 8 컴포넌트 병렬 설계 → 일관성·실현가능성 비평("NOT READY TO CODE" 판정) → 마스터 정정.
> 전략 상위문서: `harness-teardown-and-strategy.md` (Mode A 디폴트 / 개인·내부용 / M0 넓게 / 30개 전면 마이그레이션=M2)

---

## 0. 비평가 지적에 대한 마스터 결정 (코딩 전 확정)

| # | 비평가 지적 | 마스터 결정 |
|---|---|---|
| F1 | settings.json hooks의 `if`/`id` 필드는 **실재하지 않음** | ✅ 실제 스키마 `{matcher, hooks:[{type,command,timeout}]}`로 재작성. 경로 필터는 **셸 스크립트 내**에서 `tool_input.file_path`로 |
| F2 | per-node write-lock이 미검증 가정(distinct session_id)에 의존 | ✅ **M0에서 런타임 write-lock 훅 전면 제거.** 단일사용자 도구엔 위협모델 부재 + Mode A 파이프라인은 순차 단일-writer 보장. `harness.lock`은 **validate 시점 정적 중복검사**로만 잔존 |
| F3 | harness.lock 값모델 2개 충돌 / 훅 경로 2개 | ✅ F2로 소멸(런타임 훅 없음). lock은 `path→node_id` 정적 맵 1개만 |
| F4 | 단위 불일치(warrant USD vs budget 토큰) | ✅ **토큰 단일단위.** warrant가 토큰 추정 → `budget.total_tokens` 직접 채움. USD는 `TOKENS_PER_USD` 상수로 표시용 2차 뷰 |
| F5 | **graph.json·agent파일·스키마를 쓰는 컴포넌트가 없음**(최대 갭) | ✅ **Module 0 "메타스킬 writer" 신규 추가** — 사용자 요청→spine·agent·스키마 생성. M0 범위에 포함 |
| F6 | role-class 매핑 미정의 | ✅ 실제로는 model-tier의 `baseRoleClass()`가 **이미 해결**. 정규 SoT로 승격 |
| F7 | MANIFEST 콘텐츠주소 evolve 원장 과설계 | ✅ **evolve 원장 M2 연기.** M0 MANIFEST는 최소 provenance만 |
| F8 | 연구급 blind/multi-run eval 과설계 | ✅ **M0 = 단일 scorecard 1회(C2 vs C3).** full blind/n-run/C1 → M1 |

**추가 통일(마스터):** 두 설계자가 deep-research 인스턴스를 다르게 잡음 → **정규 graph 1개로 통일**: `gather(haiku) → fetch(haiku) → verify(reflect-then-revise: critic=opus, reviser=sonnet, max_rounds=2) → synthesize(opus)`. agent 4종: researcher/fetcher/verifier/synthesizer. (전략 release combo #1 "Pipeline + reflect-then-revise"와 일치, 이미 완전한 runnable workflow.js 존재.)

**해소된 미검증 질문:** Workflow resume 캐시 키 = `(prompt, opts)` (도구 명세 확정). 따라서 노드 프롬프트 템플릿을 바꾸면 그 호출부터 캐시 무효 → 정밀 부분재실행 동작 확정.

---

## 1. M0 컴포넌트 의존 지도

```
사용자 요청
   │
   ▼
[M0-0] 메타스킬 writer (harness-creator 스킬)          ← F5 신규
   ├─ [M0-5] warrant 게이트 (필요? + 토큰 비용밴드)     ← F4 토큰단위
   ├─ graph.json 저작 ──────────────┐
   ├─ agent .md 4종 저작            │
   └─ schemas/*.json 저작           │
                                    ▼
[M0-1] graph.json (SPINE, 정적계약) ◄─── [M0-2] model-tier 정책(role-class SoT) ← F6
                                    │
        ┌───────────────┬──────────┴───────────┬─────────────────┐
        ▼               ▼                       ▼                 ▼
[M0-3] workflow.js   [M0-4] validate_      [M0-7] MANIFEST    [M0-6] hooks
 emitter (Mode A      harness.py            (최소 provenance   (SubagentStop
 런타임)              (정적 게이트)          + 정적 lock검사)    토큰로그만) ← F2,F7
        │
        ▼
  Workflow({scriptPath}) 실행 = C2 arm
        │
        ▼
[M0-8] head-to-head eval (단일 scorecard, C2 vs C3) ← F8
```

---

## 2. [M0-0] 메타스킬 writer — `harness-creator` 스킬 (F5 신규, 최대 갭 해소)

다른 7개가 모두 READ하는 `graph.json`·agent파일·스키마를 **저작**하는 주체. 이게 곧 "CYS Harness Creator" 본체다.

**입력:** 사용자 자연어 요청. **출력:** 완성된 `<harness>/` git repo (아래 파일트리).

**절차 (스킬 SKILL.md 워크플로우):**
1. **warrant 게이트(M0-5)** 호출 → `{answer-directly | single-agent | build-harness}`. build-harness면 topology + decision_mechanism 제안 + n_agents.
2. **도메인 분해** → 노드 목록(id, 역할). 각 역할명을 `baseRoleClass()`(M0-2)에 통과시켜 role-class 확정.
3. **graph.json 저작(M0-1 스키마 준수)** — `harness_version="0.1.0"`의 **단일 writer는 이 스킬**(F-incoherence 해소). `resolveModel()`로 `node.model` 채움. budget.total_tokens = warrant 추정 토큰.
4. **agent .md 4종 저작(M0-2 frontmatter 계약)** — name/description/model/model_rationale/tools.
5. **schemas/*.json 저작** — 각 `node.output_schema` 파일(findings/critique/report 등).
6. **emit(M0-3)** → `.harness/workflow.js`.
7. **validate(M0-4)** → 실패 시 생성 중단·보고.
8. **비용밴드 표시 → 승인 → `Workflow({scriptPath})` 실행.**
9. **git init + commit** (rollback substrate).

**M0 산출 파일트리:**
```
deep-research/                       # ← git repo
├── .claude/
│   ├── skills/deep-research-orchestrator/SKILL.md   # graph의 사람용 뷰(phase-count는 README와 일치)
│   ├── agents/{researcher,fetcher,verifier,synthesizer}.md
│   └── settings.json                # hooks: SubagentStop 토큰로그만 (M0)
├── .harness/
│   ├── graph.json                   # SPINE
│   ├── workflow.js                  # emit 결과 (Mode A 런타임)
│   ├── harness.lock                 # path→node_id 정적 맵 (validate용, 런타임 훅 없음)
│   ├── MANIFEST.json                # 최소 provenance
│   └── runs/log.jsonl               # SubagentStop 토큰 로그(추가됨)
├── schemas/{findings,critique,report}.json
├── evals/deep-research.scorecard.json   # M0-8 단일 scorecard fixture
├── validate_harness.py
├── model-tier-policy.js
├── warrant.py
└── README.md                        # phase-count == SKILL.md (validator V_DOCDRIFT)
```

---

## 3. [M0-1] graph.json — SPINE (정적 계약)

마스터 고정 spine + 조건부 유효성. `$id`는 프로젝트 관례에 맞춰 **bare-filename**(`graph.schema.json`). 전체 JSON Schema(draft 2020-12)는 설계 원문 보존(요지):

**필수 top:** `schema_version("0.1") · harness_name(kebab) · harness_version(semver) · execution_mode(workflow|team) · topology(pipeline|dispatch|producer-reviewer) · budget{total_tokens:int, approval_required:bool} · nodes[] · edges[]`

**node 필수:** `id · agent · model(haiku|sonnet|opus) · decision_mechanism(single|majority-vote|debate-with-judge|reflect-then-revise) · mechanism_params · inputs[] · outputs[] · write_paths[] · output_schema(""허용) · retries · on_exhaust(proceed-with-gap|force-pass|escalate) · max_rounds`

**조건부 유효성(스키마 if/then + validator 보강):**
- `majority-vote` → `mechanism_params.n` 홀수 ∧ `quorum ≤ n` ∧ `tie_break∈{first,highest-confidence}` ∧ n ≤ 5(MAX_VOTERS)
- `debate-with-judge` → `mechanism_params.judge` 필수
- `reflect-then-revise` → `mechanism_params.critic` 필수 ∧ `max_rounds ≥ 1`
- `edges`는 **순서(ordering)만**, TaskCreate depends_on 아님. pipeline=선형체인, dispatch=단일소스 팬아웃, producer-reviewer=2노드 사이클 허용.
- 선택 추가필드(spine 미개명): `node.expected_tokens(default 8000)`, `node.tier_override_reason`.

**정규 deep-research graph.json (M0 dogfood):**
```json
{
  "schema_version": "0.1",
  "harness_name": "deep-research",
  "harness_version": "0.1.0",
  "execution_mode": "workflow",
  "topology": "pipeline",
  "budget": { "total_tokens": 600000, "approval_required": true },
  "nodes": [
    { "id":"gather","agent":"researcher","model":"haiku","decision_mechanism":"single",
      "mechanism_params":{}, "inputs":["_workspace/00_input/query.md"],
      "outputs":["_workspace/01_gather/findings.json"], "write_paths":["_workspace/01_gather/"],
      "output_schema":"schemas/findings.json","retries":1,"on_exhaust":"proceed-with-gap","max_rounds":1 },
    { "id":"fetch","agent":"fetcher","model":"haiku","decision_mechanism":"single",
      "mechanism_params":{}, "inputs":["_workspace/01_gather/findings.json"],
      "outputs":["_workspace/02_fetch/findings.json"], "write_paths":["_workspace/02_fetch/"],
      "output_schema":"schemas/findings.json","retries":1,"on_exhaust":"proceed-with-gap","max_rounds":1 },
    { "id":"verify","agent":"verifier","model":"sonnet","decision_mechanism":"reflect-then-revise",
      "mechanism_params":{"max_rounds":2,"critic":"opus"}, "inputs":["_workspace/02_fetch/findings.json"],
      "outputs":["_workspace/03_verify/findings.json"], "write_paths":["_workspace/03_verify/"],
      "output_schema":"schemas/findings.json","retries":0,"on_exhaust":"proceed-with-gap","max_rounds":2 },
    { "id":"synthesize","agent":"synthesizer","model":"opus","decision_mechanism":"single",
      "mechanism_params":{}, "inputs":["_workspace/03_verify/findings.json"],
      "outputs":["_workspace/04_report/report.json"], "write_paths":["_workspace/04_report/"],
      "output_schema":"schemas/report.json","retries":0,"on_exhaust":"escalate","max_rounds":1 }
  ],
  "edges": [
    {"from":"gather","to":"fetch"}, {"from":"fetch","to":"verify"}, {"from":"verify","to":"synthesize"}
  ]
}
```

---

## 4. [M0-2] model-tier 정책 — role-class SoT (F6 해소)

`model-tier-policy.js` 가 **role-class 매핑의 단일 진실원**. `baseRoleClass(id,agent)` 키워드 매처가 비평가가 "미정의"라 한 갭을 이미 메움.

- **TIER_BY_ROLE_CLASS**: `gather/extract/format/qa-scan→haiku · voter/debater/reviser→sonnet · synthesis/judge/critic/architecture→opus`
- **roleClassOf(node)**: decision_mechanism이 sub-role tier를 오버라이드(vote→voter, debate→debater, reflect→reviser; judge/critic은 mechanism_params에서 별도, 디폴트 opus). 그 외 `baseRoleClass()` 키워드 매칭, 미매칭은 **synthesis(opus)로 fail-safe-expensive** → validator가 명시 강제.
- **resolveModel(node)**: 명시 model 우선, 없으면 default map.
- **frontmatter 필수**: `model:` + `model_rationale:`(≤120자).
- **validator 규칙(이 컴포넌트 소유)**: V1 model/rationale 누락=error · V2 pure-retrieval 역할에 opus=warn(`tier_override_reason` 있으면 warn, 없으면 error) · V3 node.model≠agentFile.model=error.
- **비용가중(토큰단위, F4)**: `TIER_COST_WEIGHT={haiku:1,sonnet:4,opus:20}` (블렌디드 비율). 가중치는 warrant 비용밴드 입력.

**deep-research tier 표(정규 graph 기준):**
| node | agent | role-class | mech | model | 비고 |
|---|---|---|---|---|---|
| gather | researcher | gather | single | haiku | 순수 검색 |
| fetch | fetcher | gather | single | haiku | 소스 fetch/정리 |
| verify | verifier | reviser+critic | reflect-then-revise | sonnet(reviser)+opus(critic) | critic=opus는 mechanism_params |
| synthesize | synthesizer | synthesis | single | opus | 교차 합성 |
V2 자체검사: opus는 verify-critic·synthesize(둘 다 비-retrieval)만 → TIER_OVERSPEND 없음.

---

## 5. [M0-3] workflow.js emitter — Mode A 런타임 (핵심 산출)

`emit(graph, agents_dir, schemas_dir) -> str` 순수함수. graph.json → runnable Workflow `.js`. **wall-clock/RNG 미사용**(resume 안전), meta는 pure literal.

**매핑:** topology→pipeline()/parallel()/while루프 · 각 node→`node_<id>()` async fn · decision_mechanism→정확한 JS 래퍼(single=1콜 / majority=parallel(N)+순수JS reduce(quorum,tie_break) / debate=루프+judge agent() / reflect=루프(critic→reviser)) · node.model→`agent({model})` · output_schema→emit시점 인라인된 `agent({schema:S.x})` · node.agent→`agent({agentType})`.
**예산:** `budget.total`=HARD ceiling(도구 네이티브, spent≥total시 throw). emit는 fan-out 전에 `ensure(min)` 소프트가드만 추가. approval_required→**정적 PRE-FLIGHT 비용밴드**를 선두 주석+반환값으로(런타임 토큰합산 훅 불가, F-platform).
**resume:** 토소트 tie=배열인덱스 → 호출순서 안정. 라벨=`<id>`/`<id>#<k>`/`critic.r<r>`. 캐시키=(prompt,opts) → 변경노드부터 라이브 재실행.

**정규 deep-research `workflow.js`(emit 결과, 완전 runnable):** ※ 설계 원문의 전체 스크립트를 그대로 채택. 골격:
```js
// AUTO-EMITTED from graph.json (schema_version 0.1). DO NOT EDIT BY HAND.
// PRE-FLIGHT COST BAND: ~95k..600k tokens, ≤7 calls (haiku×2 gather,fetch | opus×2 critic | sonnet×2 reviser | opus×1 synth)
export const meta = { name:"deep-research", description:"... (Mode A, schema_version 0.1)",
  phases:[ {title:"gather",detail:"agent=researcher model=haiku mech=single"},
           {title:"fetch", detail:"agent=fetcher model=haiku mech=single"},
           {title:"verify",detail:"agent=verifier model=sonnet mech=reflect-then-revise critic=opus"},
           {title:"synthesize",detail:"agent=synthesizer model=opus mech=single"} ] };
export default async function ({ agent, parallel, pipeline, phase, log, budget, args }) {
  const S = { findings:{...}, critique:{...}, report:{...} };          // emit시점 인라인 JSONSchema
  function ensure(min){ if(budget.total && budget.remaining()<min){ log(`budget guard`); throw new Error("BUDGET_GUARD"); } }
  const P = { gather:(q)=>`...`, fetch:(p)=>`...`, critic:(d,r)=>`...`, reviser:(d,c,r)=>`...`, synth:(f)=>`...` };
  async function node_gather(i){ phase("gather"); return await agent(P.gather(i),{label:"gather",phase:"gather",model:"haiku",agentType:"researcher",schema:S.findings}); }
  async function node_fetch(p){ phase("fetch"); return await agent(P.fetch(p),{label:"fetch",phase:"fetch",model:"haiku",agentType:"fetcher",schema:S.findings}); }
  async function node_verify(p){ phase("verify"); let d=p;            // reflect-then-revise, max_rounds=2
    for(let r=0;r<2;r++){ ensure(20000);
      const c=await agent(P.critic(d,r),{label:`critic.r${r}`,phase:"verify",model:"opus",agentType:"verifier",schema:S.critique});
      if(!c||c.approved) break;
      d=await agent(P.reviser(d,c,r),{label:`reviser.r${r}`,phase:"verify",model:"sonnet",agentType:"verifier",schema:S.findings}); }
    return d; }
  async function node_synthesize(p){ phase("synthesize"); ensure(30000); return await agent(P.synth(p),{label:"synthesize",phase:"synthesize",model:"opus",agentType:"synthesizer",schema:S.report}); }
  const seed=(args&&args.query)?args.query:"(query.md in _workspace/00_input/)";
  const [report]=await pipeline([seed], p=>node_gather(p), p=>node_fetch(p), p=>node_verify(p), p=>node_synthesize(p));
  log(`done: ${report?report.title:"no report"}`); return report;
}
```
실행(C2 arm): `Workflow({scriptPath:"deep-research/.harness/workflow.js", args:{query:"<topic>"}})`. resume: `+resumeFromRunId` → gather/fetch 캐시, verify부터 라이브.

---

## 6. [M0-4] validate_harness.py — 정적 게이트 (런타임 프리미티브 0)

CLI: `validate_harness.py <harness_dir> [--json]`. exit `0`=pass, `1`=error, `2`=warn-only. 출력: 머신리더블 JSON 리포트. **체크(요지):**
- `AGENT_EXISTS` (error): 모든 node.agent → `.claude/agents/<agent>.md` 존재
- `AGENT_FRONTMATTER` (error): name+description+model+model_rationale 존재
- `TIER_MISSING/MISMATCH` (error) · `TIER_OVERSPEND` (warn): M0-2 V1/V2/V3
- `GRAPH_SCHEMA` (error): graph.json이 graph.schema.json 통과 + 조건부유효성(n홀수/quorum/judge/critic)
- `SCHEMA_FILE_EXISTS` (error): 모든 비-"" output_schema 파일 존재 + valid JSON
- `EDGE_INTEGRITY` (error): edges가 존재 node 참조, pipeline 단일소스/사이클없음(producer-reviewer 제외)
- `WRITE_PATH_OVERLAP` (error): **harness.lock 정적검사** — 두 노드가 같은 write_path 소유 금지 (F2: 런타임 훅 대체)
- `ABSOLUTE_PATHS` (error): 상대경로 금지
- `NO_COMMANDS` (error): `.claude/commands/` 아래 파일 0
- `DEAD_REFERENCE` (error): 문서/스크립트/훅이 가리키는 경로·도구 실재
- `DOC_DRIFT` (error): README phase-count == orchestrator SKILL.md phase-count (W11 수정)

**deep-research 실행 출력 예:** 정상 시 `{"status":"pass","errors":[],"warns":[]}`. researcher.md 삭제 후 → `{"status":"fail","errors":[{"code":"AGENT_EXISTS","node":"gather","msg":"..."}]}` (M0 성공기준 2).

---

## 7. [M0-5] warrant 게이트 + 비용밴드 (F4 토큰단위, 단순화)

비평가 과설계 지적 반영 → **6술어 분류기를 경량화**. 핵심만:
- **off-ramp 판정:** `distinct_expertise_domains < 2 ∧ ¬dependent_or_parallel_stages` → `single-agent` 또는 `answer-directly`. 아니면 `build-harness`.
- **팀 SIZE:** `n_agents = min(distinct_expertise_domains, MAX_FANOUT=5)`. 초과 시 "2단계 합성/도메인 묶기" 경고.
- **비용밴드(토큰 단일단위, F4):**
  `estTokens(node) = expected_tokens(default 8000) × fanout × (retries+1)`,
  `fanout`: single=1 / majority=n / debate=2·max_rounds+1 / reflect=2·max_rounds.
  `weightedUnits = Σ estTokens × TIER_COST_WEIGHT[model]`.
  `total_tokens 추정 = Σ estTokens` → **graph.budget.total_tokens 직접 채움**(하드 ceiling과 동일 단위).
  표시밴드: `<5e5=LOW / <5e6=MEDIUM / ≥5e6=HIGH`. USD는 `≈ total_tokens / TOKENS_PER_USD[tier]` 2차 표시.
- **deep-research:** 4 도메인(검색/fetch/검증/합성) but 순차파이프 → n_agents=4 (≤5 OK). 추정 ≈280k weighted units → **LOW**, total_tokens≈600k. `build-harness(pipeline, reflect-then-revise)` 판정.

---

## 8. [M0-6] hooks — 실제 스키마, M0 최소화 (F1·F2)

실제 settings.json 훅 스키마는 `{matcher, hooks:[{type,command,timeout}]}` **뿐**. `if`/`id` 없음. **M0는 write-lock 런타임 훅 제거(F2)** → 남는 훅은 **SubagentStop 토큰로그 하나**(유일하게 실현가능·best-effort):
```json
{
  "hooks": {
    "SubagentStop": [
      { "matcher": "*",
        "hooks": [ { "type":"command",
          "command":"python3 .claude/hooks/log_tokens.py",
          "timeout": 5000 } ] }
    ]
  }
}
```
`log_tokens.py`: stdin JSON에서 session_id/exit/(가용시)usage 추출 → `.harness/runs/log.jsonl` append. **명시 한계:** 플랫폼이 per-call 토큰을 hook stdin에 신뢰성있게 주지 않음 → 토큰은 coarse 휴리스틱(또는 transcript 파싱). 라이브 abort 아님(사후 기록만). active-team 훅은 Mode B 전용이라 M0 제외.

---

## 9. [M0-7] MANIFEST + harness.lock (F7 evolve 원장 연기)

- **harness.lock** (정적, 런타임 훅 없음): `{ "<write_path>": "<node_id>" }` 맵. validator `WRITE_PATH_OVERLAP`가 소비. 끝.
- **MANIFEST.json** (M0 최소 provenance): `{ harness_version, generated_by_run_id, nodes:[{id,agent,model}], artifacts:[path], git_sha(commit 후 stamp) }`. **콘텐츠주소 input_hash·def_hash·minimal-re-run 원장은 M2 evolve로 연기.** (Workflow 자체 resumeFromRunId가 within-run 캐시 제공하므로 M0엔 cross-run 원장 불요.)
- 타임스탬프/해시는 **run 종료 후 래퍼가 stamp**(workflow.js 내부 wall-clock 금지).

---

## 10. [M0-8] head-to-head eval (F8 단일 scorecard)

**M0 = 단일 discriminating-assertion scorecard 1회, 2-way(C2=CYS vs C3=no-harness).** (C1=원본 harness + blind/n-run/2-grader → M1.)
- **fixture** `evals/deep-research.scorecard.json`: 1개 실제 deep-research 쿼리 + gold-labeled discriminating assertion 6~8개(예: "모든 사실문장에 inline citation", "≥3 독립소스 교차검증", "반박된 주장 제거됨", "출처 URL 실재").
- **runner:** C2 = `Workflow({scriptPath})` 출력 / C3 = 단일 general-purpose agent 동일쿼리. 각 1회.
- **grader:** assertion별 pass/fail(gold 시드), `pass_rate` 비교.
- **승리(가설값):** C2 pass_rate ≥ C3 + 15pp. 미달 시 **정직 보고**("이 도메인 미능가"). 
- **report skeleton:** `{schema_version, harness_version, query, C2:{pass_rate,passed[]}, C3:{...}, delta_pp, verdict}`.

---

## 11. M0 빌드 순서 & 성공기준

**코딩 순서(의존순):**
1. `model-tier-policy.js` (role-class SoT, 순수함수, 가장 확실) → 단위테스트
2. `graph.schema.json` + 정규 `deep-research/.harness/graph.json`
3. `validate_harness.py` (위 둘 소비) → graph 망가뜨려 fail 확인
4. agent .md 4종 + schemas 3종 (메타스킬 writer가 저작할 산출물의 손저작 버전)
5. `emit_workflow.py` → 정규 `workflow.js` 생성 → validate 통과
6. `warrant.py` (토큰 비용밴드)
7. settings.json + `log_tokens.py`
8. `harness-creator` 스킬(M0-0): 1~7을 사용자요청→파일트리로 묶는 오케스트레이션
9. `Workflow({scriptPath})` 실행(C2) + `evals` scorecard(C3) → head-to-head 1회

**성공기준(갱신):**
1. ✅ `harness-creator`가 deep-research 요청 → 완성 git repo(파일트리) 생성
2. ✅ `validate_harness.py`가 (a) 정상 harness PASS, (b) agent참조 삭제 시 FAIL
3. ✅ `workflow.js`가 `budget.total` 도달 시 정지 + `resumeFromRunId`로 verify부터 재개
4. ✅ warrant가 단순 단일작업을 `single-agent`/`answer-directly`로 분류 + 비용밴드(토큰) 표시·승인
5. ✅ head-to-head: C2 vs C3 scorecard 1회 산출(능가 or 정직 미달보고)
6. ✅ `log_tokens.py`가 SubagentStop마다 `runs/log.jsonl` append (coarse 허용)

**M0에서 명시적으로 안 하는 것(scope-cut):** 런타임 write-lock 훅 / MANIFEST 콘텐츠주소 evolve 원장 / blind·n-run·C1 eval / Mode B 팀 런타임 / 30개 마이그레이션(=M2) / OSS 거버넌스 툴체인(=개인용 제거).

**M2로 넘긴 검증과제:** workflow.js `agent()`마다 distinct session_id가 hook stdin에 오는지 — write-lock 재도입 시에만 필요. M0은 불요(런타임 훅 없음).
