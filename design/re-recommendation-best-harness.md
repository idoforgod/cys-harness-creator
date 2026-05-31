> ⚠️ **PRE-PIVOT 역사 스냅샷 (2026-05-29 era, 프리미티브 피벗 *이전*).** 이 문서의 디스크-상태 단언("git tracks 0 files", "factory-native 테스트 0", "perf HYPOTHESIS-grade")은 그 후 바뀌었다. **현재**: repo 커밋됨, 팩토리 자체 테스트 134개(`tests/test_factory.py`), n=5 stamped eval(`examples/deep-research/evals/*.verdict.json`), `workflow.js` 은퇴·프리미티브 기질이 제품, prompt-runner는 산출 하네스에서 제외. 현 상태는 `skills/harness-creator/references/IMPLEMENTATION-STATUS.md` 우선 — 아래는 역사 기록.

All claims verified on disk. The 35 `test_*.py` are 100% inherited genome (prompt-runner + hooks transplanted into children) — zero are factory-native. git tracks 0 files. Perf artifacts self-confess HYPOTHESIS-grade. No SubagentStop/token logs exist. Now I'll deliver the re-recommendation.

---

# cys-harness-creator RE-RECOMMENDATION — 다음에 무엇을 만들 것인가

> 원칙: harness creator의 가치 = **그것이 만든 harness의, 증명된, 동작하는 품질** ÷ 만드는 노력. 기능 개수가 아니다.
> 아래는 리포지토리 디스크 상태를 직접 검증한 뒤 작성했다. 검증 결과는 각 항목에 명시한다.

---

## 0. 디스크 검증 결과 (먼저, 가정 명시)

이 추천의 전제가 되는 5가지를 직접 확인했다. 전부 갭 분석과 일치한다.

| 주장 | 검증 명령 | 결과 |
|------|----------|------|
| 트리가 git에 untracked | `git ls-files` → 0 | **사실.** 엔진·예제·증거 0개 커밋됨 |
| perf 증거가 hand-authored 샘플 | runs.json `_note` | **사실.** "kept HYPOTHESIS-grade until re-measured from SubagentStop token logs" 자기고백 |
| 실제 token log 0개 | `grep -rl SubagentStop\|token_count` | **사실.** 매칭은 전부 설계문서/주석, 실제 로그 0 |
| 상수가 미보정 | constants.json `_note` | **사실.** "All values are HYPOTHESIS-grade" |
| factory 자체 테스트 0개 | `find test_*.py` → 35개 | **사실.** 35개 전부 inherited prompt-runner/hooks. factory-native(emit/validate/warrant) 테스트 **0개** |

추가 확인: emit은 byte-deterministic, validate 게이트는 통과 (= 검증된 결정론적 back-half는 진짜다). `.harness/`에 `workflow.js`는 있으나 run-state 산출물 0개, `verification-logs/`·`pacs-logs/`는 `.gitkeep`만. **즉 검증된 가치는 deterministic back-half뿐이고, 그것이 전체 주장 가치의 ~1/5을 덮는다.**

---

## 1. 무엇이 '최고'를 결정하는가 (가장 중요한 3가지)

harness creator는 메타-도구다. "최고"는 기능이 많을 때가 아니라 **만들어낸 harness가 디스크 위에서 증명 가능하게(reproducibly) 더 낫고, 실제로 동작하고, 반복적으로 그렇게 만들어질 때** 달성된다. 순서가 곧 의존성이다 — 위가 안 서면 아래는 무의미하다.

1. **증명된 우월성 (PROVEN SUPERIORITY)** — 생성된 harness가 (a) no-harness 대비, 그리고 (b) 라이벌/수작업 대비 더 낫다는 것이, **clean checkout에서 재실행 가능한 stamped 산출물**로 증명될 것. 지금 이게 0이다. `+38pp`가 재실행하면 사라진다면 그것은 자산이 아니라 부채다. **이 게이트가 0인 한, 아래 전부의 검증 가치가 0 근처로 캡된다.**

2. **기능적 진실 (FUNCTIONAL TRUTH)** — 측정한 것과 출하한 것이 **같은 객체**일 것. 지금 h2h는 inline equivalent runner로 돌았고, custom agentType resolution을 가진 **literal emitted `workflow.js`는 단 한 번도 Mode-A로 실행된 적이 없다.** 증명(1)과 제품(디스크의 파일)이 두 개의 다른 물건이다. literal 파일이 안 돌면 이건 "그럴듯한 이야기를 가진 코드 생성기"다.

3. **신뢰할 수 있는 생성 = 진짜 factory (RELIABLE GENERATION)** — domain → valid·runnable harness를 자동화·게이트된 단계로. 단, *증명 안 된 harness를 안정적으로 찍어내는 factory*는 *증명된 harness 하나를 만드는 수작업*보다 못하다. 그래서 3순위다. 현재 back-half(emit)는 진짜 결정론적 factory지만, front-half(domain→graph.json+agents+schemas)는 100% LLM이 prose 따라가는 것 — 원본과 같은 의존성이다.

**핵심 한 줄**: 상위 2개(증명+기능, 가중치 48%)는 단 하나의 원칙을 인코딩한다 — **아무도 검증 못 하는 기능은, 증명된 동작 코어보다 가치가 낮다.** 가장 높은 레버리지의 단일 행동은 갭#1+#3을 함께 닫는 것: `make eval`이 **literal emitted workflow.js를 실행해서** stamped head-to-head 산출물을 재생성하게 만드는 것. 이 한 수가 미검증 가중치의 가장 큰 블록(48%)을 획득된 가중치로 바꾼다 — 어떤 신규 기능보다 가치가 크다.

---

## 2. 우선순위 추천 (P0 / P1 / P2)

표기: **[PROVES value]** = 이미 만든 것의 검증 / **[FEATURE]** = 새 능력 추가. 의도적으로 PROVES를 위로 올린다.

### P0 — 증명 (이것 없이는 나머지가 hypothesis다)

#### P0-1. literal workflow.js를 진짜로 한 번 돌리고, stamped 증거로 박제 **[PROVES value]** · 노력 M
- **무엇**: `examples/deep-research`를 active project로 열고, 그 **literal `.harness/workflow.js`**를 작은 `budget.total`로 Workflow 툴에서 1회 실행. agentType이 child의 `.claude/agents`에서 resolve되는지, schema-validated 출력이 node→node로 흐르는지, resume가 첫 변경 node에서만 재진입하는지 확인. **run-state 산출물을 canonical "it runs" 증거로 persist.**
- **왜 P0**: 갭#3(FUNCTIONAL TRUTH). 측정 대상과 출하 대상을 같은 객체로 만드는 단 하나의 행동. 이게 서기 전엔 #1의 숫자는 다른 물건에 관한 것이다. `.claude/agents`에 4개 role이 이미 존재하므로 **유일한 미검증 링크는 "literal 파일이 active project로 도는가" 뿐** — 가장 싼 검증이다.
- **산출물**: `examples/deep-research/.harness/` 안의 실제 run-state 1개 + 실행 transcript.
- **검증**: run-state 파일이 존재하고, resume 재실행이 0-token으로 첫 변경 node부터.

#### P0-2. stamped head-to-head를 literal 파일로 재생성, 손으로 쓴 샘플 폐기 **[PROVES value]** · 노력 M
- **무엇**: P0-1의 literal workflow.js를 C2(CYS pipeline)/C3(no-harness) 두 조건에서 고정 query로 실행 → 실제 **SubagentStop token count + scorecard** 캡처. `h2h_aggregate.py` + `lift_gate.py`가 **signed artifact**(model-id + git-sha + harness-version + raw per-run token logs + timestamp)를 `evals/`에 STAMP. hand-authored `deep-research.runs.json` / `lift-gate-fixture.json`을 **stamped 실측으로 교체.**
- **왜 P0**: 갭#1(PROVEN SUPERIORITY, 가중치 26%). 도구 전체 테제. 현재 디스크의 perf 증거는 자기고백한 fiction이다. **floor는 no-harness를 이기는 것 (non-negotiable)**, rival 이기는 건 stretch. 최소 바: N≥10 task, blind/rubric, CI band 통과.
- **산출물**: `make eval` 한 줄 → clean checkout에서 재실행 가능, 동일 verdict (tolerance band 내).
- **검증**: 재실행 시 verdict 재현. _note에서 "HYPOTHESIS" 문구 제거 가능.

#### P0-3. 트리를 git에 커밋, 그 SHA를 evidence anchor로 **[PROVES value]** · 노력 S
- **무엇**: cys-harness-creator 트리를 `git add` (`.gitignore`로 generated run-state/`__pycache__`만 제외). 알려진 SHA에 커밋. 그 SHA를 `h2h_aggregate.py`가 산출물에 stamp하는 calibration/evidence anchor로.
- **왜 P0**: 검증한 대로 `git ls-files` = 0. **엔진도, 예제도, (샘플)증거도 아무것도 커밋 안 됨.** reproducibility의 전제조건 — P0-2의 stamp가 가리킬 SHA가 없으면 stamp가 무의미하다. 노력 S, 레버리지 큼.
- **산출물**: known SHA 1개, anchor로 사용.
- **검증**: `git ls-files | wc -l` > 0, stamp에 SHA 포함.

#### P0-4. factory 자체 self-test (binary 0→1) **[PROVES value]** · 노력 M
- **무엇**: 얇은 `tests/`: (a) emit golden-file — 각 example graph.json이 byte-identical workflow.js 산출 assert; (b) intentionally-broken graph.json corpus — validate가 각 error code를 raise하는지; (c) warrant·lift_gate의 known-good/known-bad 쌍. 단일 `make test`(또는 `self_test.py`)로 wire — **inherited genome 테스트와 분리.**
- **왜 P0**: 갭#5. 검증한 대로 디스크의 35개 `test_*.py`는 **전부 inherited prompt-runner/hooks** — factory 엔진에 대해 아무것도 증명 안 함. factory-native 테스트 0개. 미검증·미테스트 도구는 silently degrade한다 (refactor가 emit 결정론을 깨도 아무도 모름). DURABILITY의 binary 0→1.
- **산출물**: `make test` 1개, factory tool 전용.
- **검증**: `make test` green, 의도적으로 emit 1줄 깨면 red.

> **P0 묶음의 정수**: P0-1+P0-2가 갭#1+#3을 함께 닫는다 = 미검증 48% → 획득. P0-3는 그 전제(SHA), P0-4는 그것이 silently 부서지지 않게 지키는 가드. 이 4개가 "promising prototype" → "증명된 코어".

---

### P1 — 진짜 factory로 + 보정 (코어가 증명된 후)

#### P1-1. front-half scaffolder/scorer (또는 validator-enforced checklist) **[FEATURE, but 핵심 능력]** · 노력 L
- **무엇**: domain → graph.json 초안을 만드는 scaffolder, 또는 최소한 LLM이 authored한 graph에 validate가 강제하는 checklist. **경계 정직성**: 도구가 "어느 단계가 결정론적이고 어느 단계가 LLM-판단(front-half)인지" 스스로 declare.
- **왜 P1**: 갭#2(RELIABLE GENERATION, 18%). 현재 "factory"는 결정론적 back-half + front-half용 prompt다. 이걸 올려야 도메인 전반에서 반복·신뢰 가능. **단 P0 뒤** — 증명 안 된 걸 안정적으로 찍는 건 후순위.
- **산출물**: scaffolder 또는 validator checklist + boundary 선언.
- **PROVES/FEATURE**: FEATURE.

#### P1-2. constants를 실측에서 보정하는 calibrate.py **[PROVES value]** · 노력 M
- **무엇**: P0-2가 token log를 만든 뒤, `calibrate.py`가 측정 분포에서 `EXPECTED_TOKENS_DEFAULT`·tier cost weight·cost band를 도출하고, 관측된 C2-vs-C3 spread에서 lift/margin threshold 재도출. provenance(sample size, git-sha)를 constants.json에 stamp.
- **왜 P1**: 갭#6. 검증한 대로 모든 상수가 자기고백 HYPOTHESIS. **calibrate의 입력(token log)이 P0-2 전엔 존재하지 않으므로 강제로 P1.** 그 전까지는 게이트 출력 텍스트에 "HYPOTHESIS" 라벨 유지.
- **산출물**: `calibrate.py` + provenance가 박힌 constants.json.

#### P1-3. AWF 철학 통합 — 검증 레이어 1개를 CYS-native로 end-to-end 동작 **[FEATURE]** · 노력 L
- → **3번 섹션에서 별도 정직 배치.** (여기 P1 하단)

---

### P2 — 차별화 검증 + DX (코어가 서고 factory화된 후)

#### P2-1. references A/B ablation **[PROVES value]** · 노력 L
- **무엇**: 4 예제에 없는 **새 도메인** 하나를 두 번 생성 — full references vs. 의도적으로 thin한 skill — emit+validate+run 후 같은 h2h scorecard로 비교. **measurably 이기는 차원만** references 유지, 나머지 trim.
- **왜 P2**: 갭#8(DESIGN INTELLIGENCE, 14%). 2,553줄 references는 같은 세션이 예제와 함께 작성 → 독립 검증 불가. **차별 테스트 안 된 design 지식 = 자신감 있는 prose와 구별 불가.** 단 P2 — design intelligence는 #1을 통해서만 관측된다. P0가 서야 측정할 scorecard가 존재.
- **산출물**: A/B run 비교 + trim 결정.

#### P2-2. failure legibility / DX 측정 **[FEATURE]** · 노력 S
- **무엇**: validate/warrant reject 시 메시지가 정확한 graph.json 수정 지점을 가리키는가 (mean turns-to-green). "domain idea → emit+validate PASS"까지 turn 수 baseline화.
- **왜 P2**: DX는 value의 분모지만, 1인 expert용 internal 도구에선 **증명된 harness를 찍는 투박한 도구 > 증명 안 된 걸 찍는 쾌적한 도구.** 1–5 서면 tiebreaker이자 compounding (마찰↓ → dogfood↑ → #1 증거↑).

---

## 3. 직전에 논의하던 AWF-철학 통합(pACS / 4계층)은 어느 우선순위인가

**정직한 배치: P1 하단 — 단, "전면 통합"이 아니라 "1개 레이어 end-to-end 증명"으로 축소해서.** (P1-3)

이유:
- **현재 100% dormant + AWF-SOT-bound (검증됨)**: `pacs-logs/`·`verification-logs/`는 `.gitkeep`만. inherited 4-layer QA/pACS validator는 children에 transplant됐지만(228 files) CYS Mode-A 경로에서 **아무것도 invoke 안 함**. 게다가 AWF SOT layout을 검증하지, CYS의 graph.json/`_workspace` 출력을 검증하지 **않는다** — 즉 CYS-native 재구현이 필요한, 동작하지 않는 스택이다.
- **순서 논리**: 이건 design intelligence/품질의 *content*다. 그러나 **증명(P0)도 안 된 코어 위에, factory화(P1-1)도 안 된 상태에서 품질 스택을 통합하는 건 미검증 위에 미검증을 쌓는 것.** AWF 통합의 가치도 결국 #1(증명된 우월성)을 통해서만 관측된다 — verification 레이어가 harness를 *measurably* 낫게 만든다는 걸 보여야 하는데, 그 scorecard는 P0 뒤에야 존재한다.
- **그래서 축소**: "4계층 전부 + pACS 전면 통합"은 함정(아래 4번). 대신 **deep-research에 가장 관련 있는 validator 1개**(예: citation/source-backing check)를 골라 **CYS `_workspace` 출력 contract로 re-point**하고, post-synthesize node나 hook으로 invoke해서 `verification-logs/`에 **실제 entry 1개**가 찍히게. **스택을 주장하기 전에 한 레이어가 end-to-end 동작함을 증명.**

> 요약: **pACS/4계층 = P1-3, 1개 레이어 end-to-end 증명으로 축소.** P0(증명)·P1-1(factory화)·P1-2(보정) 뒤. 매력적이지만 지금 들어가면 미검증 위의 미검증.

---

## 4. 하지 말 것 (feature-creep 함정)

1. **새 example harness 추가 금지.** 4개도 이미 미검증(emit+validate만 PASS, run 안 됨). 5번째는 미검증 가치를 키울 뿐. **증명 안 된 harness 1개 더 < 기존 1개를 진짜 돌리기.**
2. **references 확장 금지.** 2,553줄이 thin skill보다 낫다는 증거 0. **trim 후보지 확장 대상 아님** (P2-1 A/B 전엔 어느 쪽도 모름).
3. **AWF 4계층 전면 통합 금지.** (3번 참조) 미검증 위 미검증. 1개 레이어로 축소.
4. **dead-weight prompt-runner(128 files) "정리/리팩터" 금지.** full-genome-inheritance는 **의도된 사용자 결정**이다 — bug가 아니라 manage할 tension. 건드리지 말 것.
5. **front-half를 과설계한 scaffolder 금지.** P1-1은 "scaffolder 또는 validator-enforced checklist" — **200줄로 될 걸 50줄로.** 추측 기반 유연성·설정가능성 추가 금지.
6. **새 topology/decision-mechanism 추가 금지.** 현재 4개 mechanism이 다 *선택되긴 하는지*도 미측정 (collapse to one일 수 있음). 커버리지 검증 전 확장 금지.
7. **prose로 자동화 마케팅 금지.** front-half가 100% LLU-manual인데 "factory"로 전체를 파는 것 자체가 부채. 경계를 declare (P1-1).

---

## 5. 단일 다음 액션 (THE ONE THING)

> **`examples/deep-research`를 active project로 열고, 그 literal `.harness/workflow.js`를 작은 budget으로 Workflow 툴에서 1회 실행해서, run-state 산출물을 디스크에 박제하라. (P0-1)**

왜 이 하나인가:
- 가장 싼 검증인데 가장 큰 미검증 블록(FUNCTIONAL TRUTH)을 연다. agentType 4개가 이미 `.claude/agents`에 있으므로 (검증함) **유일한 미검증 링크는 "literal 파일이 active project로 도는가"뿐.**
- 이게 성공하면 P0-2(stamped h2h)가 즉시 가능해지고 — 둘이 합쳐 미검증 가중치 48%를 획득으로 전환.
- 이게 실패하면, **그 실패가 지금 가장 알아야 할 진실이다** ("factory가 자기 출력 파일을 못 돌린다"). 이것 위에 무엇을 더 쌓기 전에.

실행 직후 P0-3(git commit, SHA anchor) → P0-2(stamped h2h) 순. 신규 기능은 P0 4개가 green이 된 뒤에 비로소.

**판정**: 현재 검증된 가치는 deterministic back-half(emit byte-identical, validate PASS)뿐 — 주장 가치의 ~1/5. 나머지(headline perf, literal 파일 실행, references 우월성, factory 자체 정확성)는 전부 hypothesis-grade거나 session-ephemeral. "best"로 가는 길은 신규 기능이 아니라 **그 4/5를 디스크 위 증명으로 전환하는 것**이고, 그 전환의 첫 도미노가 위의 단일 액션이다.