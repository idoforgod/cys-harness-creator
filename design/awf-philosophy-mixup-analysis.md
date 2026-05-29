This is the decisive evidence. The factory brain explicitly and repeatedly states that the AWF operational machinery (context-preservation, 4-layer gates, security hooks, autopilot, ULW, pACS) is the inherited "back-half" that the factory does NOT design with — it only verifies presence. This is a deliberate front-half/back-half split. I now have everything needed to write the rigorous analysis.

---

# MIXUP 분석 — AWF ARCHITECTURE-AND-PHILOSOPHY가 harness-creator 공장두뇌(Factory Brain)에 얼마나 통합되어 설계 품질을 향상시키는가

> **분석 단위 고정.** 공장두뇌 = `skills/harness-creator/SKILL.md` + `references/`(7개) + `CONSTITUTION.md`. 이것이 *새 하네스를 설계할 때* LLM이 따르는 지침이다. 게놈 = `inherit_genome.py`가 모든 자식에 전수하는 228파일 운영기계(`genome/.claude/hooks/scripts/*`, `soul.md`, `AGENTS.md` 등). **"통합되었다"는 게놈에 있다는 뜻이 아니라 공장두뇌가 그 철학으로 *설계한다*는 뜻이다.**
>
> **실측 근거.** 공장두뇌 전문(全文) 키워드 스캔 + `validate_harness.py` 게이트 코드 + `inherit_genome.py` 전수목록 + `genome/.claude/settings.json` hook 배선을 직접 읽고 작성. 제공된 요약을 그대로 신뢰하지 않고 교차검증함.

---

## 0. 결정적 1차 증거 (판정의 근거)

공장두뇌 전체(SKILL.md + 7 references)에서 AWF arch-philosophy 핵심어 출현 빈도:

| 키워드 | 공장두뇌 파일 수 | 어디에 / 맥락 |
|---|---|---|
| `Autopilot`, `ULW/Ultrawork` | **0** | 전무 |
| `Adversarial`, `4-Layer`, `L0/L1.5/L2`, `Verification Gate`, `Anti-Skip` | **0** | 전무 (계층 명칭 자체가 공장두뇌에 없음) |
| `Abductive`, `Error Taxonomy`, `risk-score`, `predictive`, `Decision Log` | **0** | 전무 |
| `Context Preservation`, `work_log`, `knowledge-index` | **0**(영어) | "컨텍스트 보존 hook"으로 4회 — **전부 "상속받은 back-half, 설계 대상 아님"** 맥락 |
| `Hub-and-Spoke`, `GEMINI`, `Notation`, `(human)/(hook)`, `RLM`, `English-First`, `glossary` | **0** | 전무 |
| `pACS` | 2 | IMPLEMENTATION-STATUS("opt-in **연기**") + qa-guide(reviewer가 "독립 pACS 채점" 1줄) |
| `soul.md`, `AGENTS.md`, `block_destructive`, `secret` | 각 1 | **전부 testing-and-measurement.md의 `GENOME_PRESENT` 전수파일 *리스트*** — 설계지침 아님 |
| `게놈/상속` | 6~7 | **풍부**하나 "전수받는다 / 다시 만들지 않는다"는 경계선언 맥락 |

공장두뇌가 명시적으로 그은 선 (skill-writing-guide.md §6, graph-and-orchestration.md §44):

> "자식 하네스는 게놈을 통째로 물려받아 **이미** 컨텍스트 보존 hook·4계층 품질 게이트·보안 hook을 **갖고 태어난다.** 이 가이드의 저작 작업은 **앞단(front-half) 설계**에 집중한다. **상속된 뒷단(back-half) 기계는 다시 만들지 않는다.**"

이 한 문장이 mixup 구조의 전부를 규정한다: **공장두뇌는 AWF 운영철학을 "설계 변수"가 아니라 "상속 상수"로 취급한다.** 즉 대다수 AWF arch-philosophy 함수는 GENOME-ONLY다.

---

## 1. MIXUP 매핑표

각 AWF arch-philosophy 함수 → 공장두뇌 통합 상태 + 위치 + 설계품질 향상 여부.
판정: **WELL-MIXED**(SKILL/references에 있고 설계를 형성) / **PARTIAL**(언급되나 얕음) / **GENOME-ONLY**(자식에 상속되나 공장두뇌엔 부재) / **MISSING**.

| # | AWF arch-philosophy 함수 | 상태 | 어디에 (공장두뇌) | 설계품질 향상? |
|---|---|---|---|---|
| 1 | **AC-1 Quality Absolutism** | **WELL-MIXED** | CONSTITUTION AC-1; SKILL 원칙1; model-tier-policy·warrant 강제로 구체화 | **예.** "강한 소수>약한 다수", 품질임계=opus, 비용밴드 가시화로 설계 결정을 실제 형성 |
| 2 | **AC-2 Single SOT + Single-Writer** | **WELL-MIXED** | CONSTITUTION AC-2; SKILL Phase2("이 스킬만 graph.json 쓴다"); graph-and-orch §2/§6 write_paths 비중첩; harness.lock | **예.** 단일 writer가 그래프 토폴로지·write_path 설계를 직접 규율. 게다가 AWF의 `state.yaml`을 *거부*하고 `resumeFromRunId`로 대체("2-state 드리프트 금지")—철학을 능동적으로 *개선* |
| 3 | **AC-3 Code Change Protocol** | **WELL-MIXED** | CONSTITUTION AC-3; SKILL Phase5 `/code-review` 게이트; skill-writing-guide Why-not-ALWAYS | **예.** emit/validate 변경 전 영향분석 강제. 단 대상은 *공장 자체 코드*이지 자식 도메인 설계는 아님(범위 한정적이나 정직) |
| 4 | **Stem-Cell Genome / Heredity** | **WELL-MIXED**(전수 메커니즘) / **PARTIAL**(유전자 발현 철학) | SKILL Phase4 emit+inherit_genome; CONSTITUTION 상속규약; validate `W1_GENOME`·`GENOME_PRESENT`; harness.md `Inherited DNA` 섹션 | **부분.** "구조적 상속(참조 아닌 임베드)"은 충실 구현. 그러나 AWF의 "도메인별 유전자 발현(Research vs Implementation vs Data-pipeline 분화)"은 공장두뇌가 거의 다루지 않음—topology×mechanism 축이 대체하나 *발현* 어휘는 부재 |
| 5 | **4-Layer Quality Gates (L0–L2+Autopilot)** | **GENOME-ONLY** | 공장두뇌엔 "4계층 품질 게이트"가 *상속받는 back-half*로만 언급. validate가 hook *존재*만 확인 | **아니오(설계 측면).** 공장은 자식의 L0/L1/L1.5/L2 게이트 *구조를 설계하지 않는다.* lift_gate/h2h는 별개의 측정 게이트지 AWF 4계층이 아님 |
| 6 | **P1 Deterministic Pre/Post-Processing** | **PARTIAL→WELL-MIXED(재해석)** | qa-guide "코드는 거짓말 안 한다"(@fact-checker DNA); role-tier(gather/extract=haiku); architecture-patterns 결정론 emit | **예(재해석분).** "코드=결정론, LLM=판단"은 Mode-A wall-clock/RNG-free·schema강제로 *공장 설계 핵심*에 흡수됨. 단 AWF식 "데이터 살균 Python 전처리 노드"를 설계하라는 지침은 없음 |
| 7 | **Context Preservation (세션 연속성)** | **GENOME-ONLY** | "컨텍스트 보존 hook 갖고 태어난다"만 4회—**전부 "설계 안 함" 선언** | **아니오.** work_log/knowledge-index/snapshot 복원은 자식이 *상속*만. 공장은 도메인별 연속성을 설계하지 않음 |
| 8 | **Hub-and-Spoke Documentation (AGENTS.md Hub)** | **GENOME-ONLY** | `AGENTS.md`는 `GENOME_PRESENT` 전수 리스트에만 등장(1회). 1,370줄 Hub가 자식에 복사되나 공장두뇌는 이를 설계지침으로 *읽지 않음* | **아니오.** 공장은 Hub>Spoke 동기화나 spoke 매핑을 설계하지 않음. 자식이 파일을 *소유*할 뿐 |
| 9 | **pACS Self-Calibration (F/C/L, pre-mortem)** | **PARTIAL / 명시적 연기** | IMPLEMENTATION-STATUS "pACS opt-in **연기**"; qa-guide reviewer "독립 pACS 채점" 1줄 + pre-mortem 의무 | **잠재.** pre-mortem+최소1이슈는 reviewer 설계에 살아있으나, F/C/L 3차원·min()·GREEN/YELLOW/RED 색대는 공장두뇌 부재(M0 연기) |
| 10 | **Verification Protocol (L1 기준선언+재생성)** | **PARTIAL** | qa-guide "런타임 정합성 의미 게이트"; graph on_exhaust retries(max). AWF식 step별 "Verification criteria 선언→체계검사→해당섹션만 재생성(max10)"은 부분 매핑 | **잠재.** node-level retries/on_exhaust가 일부 흡수. 그러나 "단계별 검증기준 명시→PASS로그" 설계패턴은 약함 |
| 11 | **Adversarial Review (L2 @reviewer/@fact-checker)** | **WELL-MIXED**(원본 DNA로) / GENOME-ONLY(L2 계층기계) | qa-guide §4 verify-before-assert, reviewer/fact-checker를 producer-reviewer reviewer 노드로 직접 지정; examples §reuse | **예.** "적대적 검토자를 critic 노드의 베이스로 삼아라"는 *실제 그래프 설계*에 반영. 다만 validate_review.py(R1-R5)·Abductive 연계는 게놈에만 |
| 12 | **Knowledge Archive + Error Taxonomy** | **GENOME-ONLY** | 공장두뇌 0회. genome hook(update_work_log·diagnose_context)만 | **아니오.** 12종 에러분류·해결매칭·세션학습은 자식 상속. 공장 설계 무관 |
| 13 | **Predictive Debugging (risk-score)** | **GENOME-ONLY** | 공장두뇌 0회. `predictive_debug_guard.py`는 게놈에만 | **아니오.** |
| 14 | **Safety Hooks (exit 2 차단)** | **GENOME-ONLY**(설계) / 존재검증만 | validate `HOOK_REGISTERED`가 block_destructive·output_secret·security_guard·context_guard *배선 존재*만 강제 | **아니오(설계).** 공장은 도메인 위협모델로 *새 hook을 설계하지 않음*—상속분이 배선됐는지만 체크. 안전성 자체는 자식이 확실히 가짐(향상은 실재하나 *공장 설계*가 아닌 *상속*) |
| 15 | **Autopilot Mode** | **MISSING** | 공장두뇌 0회. genome docs/protocols/autopilot-execution.md만 | **아니오.** 공장은 autopilot.enabled SOT 플래그·decision-log를 설계 변수로 다루지 않음. (CYS는 warrant 사전승인이라는 *다른* 게이트 채택) |
| 16 | **ULW Mode (Ultrawork)** | **MISSING** | 공장두뇌 0회. genome docs/protocols/ulw-mode.md만 | **아니오.** Sisyphus 재시도·강제분해 강도오버레이를 공장이 설계에 안 씀 |
| 17 | **Sub-agent vs Agent Team 선택** | **WELL-MIXED**(재배선) | SKILL 원칙1(Mode-A 디폴트); architecture-patterns §8 Mode-A/B Why-not-ALWAYS; warrant single/team 제안 | **예.** AWF "품질만이 기준"을 계승하되 *디폴트를 역전*(team→workflow). 실시간 comms 필수일 때만 Mode-B—철학 충실 + 결정론으로 *개선* |
| 18 | **WHY/WHAT/HOW/VERIFY 문서분할** | **WELL-MIXED**(암묵 구현, 명시 부재) | 구조 자체가 SKILL(WHY)+architecture/graph(HOW)+qa/testing(VERIFY)로 실현. 그러나 4분할 *원칙어*는 skill-writing-guide에 명시 안 됨 | **부분.** 구조는 따르나 자식 스킬 저작 시 "WHY/WHAT/HOW/VERIFY로 나눠라"는 설계지침이 약함(progressive disclosure만 shallow 언급) |
| 19 | **RLM External Memory Objects (soul/AGENTS/template)** | **GENOME-ONLY** | soul.md·AGENTS.md는 `GENOME_PRESENT` 리스트에만. RLM 이론 0회 | **아니오.** 외부메모리 객체를 *공장이 설계*하지 않음—게놈이 통째 복사 |
| 20 | **P1 Hallucination Prevention (코드강제 정확성)** | **WELL-MIXED**(개념 승격) | CONSTITUTION "rules-as-essays→rules-as-assertions"; validate_harness ~18체크·model-tier-policy·warrant | **예.** AWF의 "산문 아닌 코드강제" 철학을 공장이 *자기 게이트*로 직접 구현. CYS의 가장 강한 통합점 |
| 21 | **Abductive Diagnosis (AD1-AD10)** | **GENOME-ONLY** | 공장두뇌 0회. diagnose/validate_diagnosis는 게놈에만 | **아니오.** |
| 22 | **Notation System ((human)/(hook)/@agent…)** | **MISSING** | 공장두뇌 0회. (team)은 4회나 *Mode-B 팀* 의미지 notation 기호 아님 | **아니오.** 공장은 graph.json 필드로 실행의미를 인코딩—AWF 6기호 표기법을 채택하지 않음(다른 접근) |
| 23 | **English-First + Translation (glossary.yaml)** | **GENOME-ONLY** | translator는 genome 공통 에이전트(examples §reuse 1줄). glossary/English-first 설계지침 0회 | **아니오.** @translator 상속만. 공장은 영어우선·glossary 일관성을 설계 변수로 안 씀 |

**집계:** WELL-MIXED 8 (#1,2,3,11,17,20 + #6·#4 부분) / PARTIAL 4 (#4,9,10,18) / GENOME-ONLY 8 (#5,7,8,12,13,14,19,21,23) / MISSING 3 (#15,16,22).

---

## 2. 잘 MIXUP된 것 (기능향상 ✓) — 증거 기반

이들은 게놈에 묻어온 게 아니라 **공장두뇌가 그 철학으로 *설계하도록* 재배선**된 것이다.

1. **AC-2 단일 SOT를 *개선하며* 흡수.** AWF는 `.claude/state.yaml`을 SOT로 둔다. CYS는 이를 *거부*하고 `MANIFEST.json`(provenance)+`graph.json`(불변계약)으로 분리, 런타임 상태는 `resumeFromRunId`에 위임("별도 state 파일 안 만든다 — 2-state 드리프트 금지", CONSTITUTION AC-2). → 철학 계승 + 명시적 개선. validate가 `WRITE_PATH_OVERLAP`·`harness.lock`으로 강제.

2. **P1 "코드강제 정확성"을 공장 자체 게이트로 승격.** CONSTITUTION의 표어 "rules-as-essays → rules-as-assertions"가 `validate_harness.py`의 ~18개 머신체크(`TIER_MISMATCH`, `TIER_OVERSPEND`, `ABSOLUTE_PATHS`, `WRITE_PATH_OVERLAP`, `RATIONALE_MISSING` …)로 실재한다. AWF의 P1 정신(LLM 판단이 아닌 코드 결정)을 *공장이 자신에게* 적용 → 설계 산출물이 일관되게 게이트를 통과.

3. **Mode-A 디폴트 = Sub-agent/Team 선택철학의 결정론적 재해석.** AWF "선택기준은 속도/비용이 아니라 품질뿐"을 계승(SKILL 원칙1)하되, 디폴트를 team→workflow로 역전(architecture-patterns §8 Why-not-ALWAYS). wall-clock/RNG-free·resume-safe가 *재현성*이라는 새 품질축을 추가 → 설계 산출물이 결정론적이 됨.

4. **AC-1을 model-tier 정책으로 구체화.** "품질 최우선"이 추상표어로 끝나지 않고 role→tier(gather/extract=haiku, voter/debater=sonnet, synthesis/judge/critic=opus, validate `TIER_MISMATCH`로 강제)로 떨어진다. AWF의 "all-opus" 안티패턴을 *교정*하면서 품질임계 노드엔 opus 보장 → 노드 매핑 설계를 실제로 형성.

5. **적대적 검토 DNA를 그래프 설계로.** qa-guide §4가 @reviewer/@fact-checker를 "producer-reviewer의 reviewer 노드 agent로 직접 지정하거나 그 프로토콜(pre-mortem, 최소1이슈, read-only)을 도메인 critic의 베이스로 삼아라"고 지시 → 적대적 검토가 자식 *토폴로지에 박힘*. verify-before-assert(reproduced/evidenced/suspected 등급)는 AWF fact-checker DNA를 코드 도메인으로 일반화한 실제 설계패턴.

이 다섯은 정직하게 **WELL-MIXED이며 설계 품질을 향상**시킨다.

---

## 3. MIXUP 안 된 것 / GENOME-ONLY / MISSING — 정직한 공백

공장두뇌가 *설계에 쓰지 않는* AWF arch-philosophy 함수들(자식은 상속하더라도):

**GENOME-ONLY (8) — 자식엔 상속, 공장 설계엔 부재:**
- **4-Layer Quality Gates(L0/L1/L1.5/L2)** — 공장두뇌에 계층 명칭조차 없음. 자식은 hook을 상속받지만, 공장은 도메인별로 어떤 검증계층을 어디 둘지 *설계하지 않는다.* lift_gate/h2h는 공장의 *별도* 측정 게이트지 AWF 4계층의 자식측 구성이 아니다.
- **Context Preservation** — "갖고 태어난다"는 선언 4회뿐. 도메인별 세션연속성·IMMORTAL 압축을 설계 안 함.
- **Hub-and-Spoke / AGENTS.md Hub** — 1,370줄 Hub가 자식에 복사되나 공장두뇌는 이를 *읽지도 설계하지도* 않음. Hub>Spoke 동기화 의무가 공장 워크플로우에 없음.
- **Knowledge Archive + Error Taxonomy**, **Predictive Debugging(risk-score)**, **Abductive Diagnosis(AD1-AD10)** — 전부 공장두뇌 0회. 순수 상속 기계.
- **Safety Hooks** — `HOOK_REGISTERED`가 4개 hook *배선 존재만* 확인. 도메인 위협모델로 *새 안전 hook을 설계하라*는 지침은 없음.
- **RLM External Memory Objects** — soul.md/AGENTS.md는 `GENOME_PRESENT` 파일목록에만. RLM 이론은 공장두뇌에 단 한 번도 안 나옴.

**MISSING (3) — 자식에 protocol 문서는 복사되나 공장도, 실질적 사용도 없음:**
- **Autopilot Mode** — 0회. CYS는 `warrant.py` 사전승인이라는 *다른 철학*(자동승인 대신 비용밴드 명시승인)을 택함. AWF autopilot.enabled/decision-log는 미채택.
- **ULW Mode** — 0회. Sisyphus 재시도·강제 task 분해 강도오버레이 미채택.
- **Notation System(6기호)** — 0회. CYS는 graph.json 필드로 실행의미 인코딩(다른 접근).
- (부수) **English-First + glossary** — translator 상속 1줄 외 설계지침 없음.

---

## 4. 이중계상(double-counting) 위험 — "통합처럼 보이나 실제론 부재"

요약문(WHAT THE FACTORY BRAIN INTEGRATES / Factory brain summary)이 통합으로 *과대계상*할 위험이 있는 항목들. **게놈에 있다는 사실이 공장 설계 통합으로 둔갑하는 지점:**

1. **"4계층 품질 게이트·컨텍스트 보존·보안 hook을 갖춘 자식이 태어난다" → 통합 아님.** 이건 *상속 사실*이다. 공장두뇌는 명시적으로 "back-half는 다시 설계하지 않는다"고 선언(skill-writing-guide §6, §371; graph-and-orch §44). 따라서 #5,7,12,13,14,21을 "통합"으로 세면 이중계상이다 — 공장은 이들로 *설계하지 않는다.*

2. **`GENOME_PRESENT` 9파일 리스트(soul.md·AGENTS.md·block_destructive·output_secret 등)를 "references에 등장" 통합으로 오인 금지.** 이 출현은 *전수파일 존재검사 목록*이지 설계지침이 아니다(testing-and-measurement.md §187). soul.md/AGENTS.md가 references에 "나온다"는 것은 통합이 아니라 *체크리스트 항목*이다.

3. **"Adversarial Review가 통합" — 절반만 참.** @reviewer/@fact-checker를 critic 노드로 *지정하는 설계지침*은 WELL-MIXED(§2-5). 그러나 L2 *계층 기계*(validate_review.py R1-R5, Abductive 연계, 색대 escalation)는 GENOME-ONLY다. "Adversarial Review 통합 ✓"라고 통째로 세면 후반부를 이중계상한다.

4. **"Genome Inheritance가 핵심 통합 [deep]" — 메커니즘은 deep, 철학은 shallow.** 전수 *메커니즘*(emit+inherit_genome+GENOME_PRESENT)은 진짜 deep 통합이다. 그러나 AWF "유전자 발현(도메인별 분화)" *철학*은 거의 미통합 — topology×mechanism 축이 *대체*할 뿐 "이 도메인은 Research-centric이니 이 유전자를 강하게 발현"식 설계어가 공장두뇌에 없다. "Stem-Cell Genome 통합 ✓"는 메커니즘에만 적용해야 정직하다.

5. **pACS — "qa-guide에 pACS 등장" ≠ 통합.** 등장 1회는 reviewer 설명의 수식어이고, IMPLEMENTATION-STATUS는 pACS를 "**opt-in 연기**"로 못박는다. pACS를 통합으로 세면 명시적 미구현을 이중계상한다.

---

## 5. 종합 판정

**Net: 공장두뇌는 AWF의 *철학적 코어*(8 core functions 중 품질절대주의·단일SOT·코드강제정확성·상속메커니즘·구조선택)를 깊고 정직하게, 때로 *개선하며* 통합했다. 그러나 AWF의 *운영 머신철학*(4계층 게이트·컨텍스트보존·자기보정pACS·자율모드·진단/예측디버깅·Hub-Spoke·표기법·번역)은 거의 전부 GENOME-ONLY 또는 MISSING이다.**

이것은 결함이 아니라 **의도된 front-half/back-half 분업**이다. 공장두뇌가 통합한 것은 "**어떤 그래프를 저작하면 원하는 오케스트레이터로 컴파일되는가**"(설계)이고, 운영기계는 게놈이 통째로 책임진다. 정직한 점수:

- **설계를 직접 형성하는 통합(WELL-MIXED 설계품질 향상):** AC-1/2/3, P1-코드강제, Mode-A, role-tier, 적대적-critic-노드, 결정론. → **강함. 그리고 AWF 원본보다 개선(state.yaml 거부, all-opus 교정, 산문→assertion).**
- **공백(GENOME-ONLY/MISSING):** 운영철학 11종. 자식은 *작동*하지만 공장은 이들로 *설계하지 않는다.* "측정 가능한 품질"(lift/h2h)은 강하나 "운영 품질"(연속성·자기보정·자율성)은 설계 사각지대.

요약 문구 "total reimplementation of the philosophical framework"는 **과장**이다. 정확히는 *철학 코어의 deep 재구현 + 운영철학의 통째 상속(설계 미통합)*이다.

### 가장 큰 공백을 메울 SKILL.md/references 구체 추가 (GENOME-ONLY/MISSING → WELL-MIXED, 설계 향상되는 것만)

1. **`references/qa-guide.md`에 "검증계층 설계 결정표" 추가** — 도메인별로 어떤 노드에 L1(의미검증)/L2(적대검토)를 *둘지* 선택규칙. 현재 reviewer 지정은 있으나 "언제 critic을 추가하고 언제 생략하나"의 *설계 판단*이 약함. → 4계층 철학을 GENOME-ONLY에서 설계변수로 끌어올림(설계 향상 ✓).
2. **`SKILL.md` Phase 9에 pACS opt-in 설계 훅 추가** — IMPLEMENTATION-STATUS가 "연기"로 둔 pACS를 *언제 켤지*(고위험 판단 노드)의 설계기준 1단락. F/C/L+pre-mortem을 synthesis/judge 노드 프롬프트에 선택적으로 박는 패턴. → 자기보정을 설계가능하게(향상 ✓).
3. **`references/architecture-patterns.md`에 "유전자 발현(domain expression)" 절** — AWF의 Research/Implementation/Data-pipeline 분화를 topology×mechanism 디폴트 프리셋으로 매핑("리서치 도메인 → dispatch+vote 기본값"). 상속메커니즘은 deep이나 *발현철학*이 shallow한 공백을 메움(향상 ✓).
4. **`references/skill-writing-guide.md`에 WHY/WHAT/HOW/VERIFY 4분할 *원칙어* 명시** — 현재 구조는 따르나 자식 오케스트레이터 스킬 저작 시 이 분할을 지시하지 않음. 1단락 추가로 자식 스킬 품질 향상(향상 ✓).

**설계를 향상시키지 *않으므로* 추가 권하지 않는 것:** Autopilot/ULW(CYS는 warrant 승인철학으로 의도적 대체), Notation 6기호(graph.json 필드가 더 강함), RLM 이론·Hub-Spoke·Error Taxonomy·Predictive/Abductive(전부 back-half 운영기계 — 게놈이 책임지는 게 올바른 분업). 이들을 공장두뇌로 끌어올리면 "back-half를 다시 설계하지 않는다"는 핵심 SOT 원칙을 위반하고 두 번째 SOT를 만든다.

---

**검증 결과 보고:** 제공된 "Factory brain summary"의 deep 통합 주장 중 **철학 코어 항목(AC-1/2/3, P1, Mode-A, role-tier, 결정론, 단일writer, 적대적 critic-노드 지정)은 실측으로 확인됨.** 그러나 운영철학 항목은 게놈 전수 사실을 통합으로 과대계상한 측면이 있어, 본 분석은 이를 GENOME-ONLY/MISSING으로 강등하여 정직하게 분리했다.

관련 파일(절대경로): `/Users/cys/Desktop/CYSjavis/cys-harness-creator/skills/harness-creator/SKILL.md`, 동 `references/`(7파일), `/Users/cys/Desktop/CYSjavis/cys-harness-creator/CONSTITUTION.md`, `/Users/cys/Desktop/CYSjavis/cys-harness-creator/validate_harness.py`, `/Users/cys/Desktop/CYSjavis/cys-harness-creator/inherit_genome.py`, `/Users/cys/Desktop/CYSjavis/cys-harness-creator/genome/`.