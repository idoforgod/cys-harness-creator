> ⚠️ **구현 현황은 [`IMPLEMENTATION-STATUS.md`](IMPLEMENTATION-STATUS.md)가 우선한다.** 이 문서의 설계 서술 중 dispatch(dynamic)/supervisor·expert-pool·hierarchical 등은 M1-deferred(미구현)이며, `.claude/commands` 비우기 규칙은 폐기됐다.

# QA 가이드 (CYS 하네스)

> 출처: 원본 `qa-agent-guide.md`을 CYS 패러다임으로 적응.

빌드/생성 하네스 안에 **QA를 어떻게 노드와 토폴로지로 박아 넣을 것인가**에 대한 설계 가이드. 실제 프로젝트(SatangSlide)에서 발견된 7개 버그 패턴과 근본 원인 분석은 그대로 보존하되, "QA 에이전트를 `.claude/agents`에 직접 쓰는" 모델 대신 **graph.json 노드 + decision_mechanism + topology**로 QA를 표현하는 CYS 방식으로 변환했다.

핵심 전환 한 줄: 원본의 "QA 에이전트"는 CYS에서 **두 가지 메커니즘**으로 분해된다 — (1) 한 노드 안에서 자기 산출물을 비평·수정하는 `reflect-then-revise`(critic 노드), (2) 생산자와 검토자를 분리해 bounded loop를 도는 `producer-reviewer` 토폴로지. 그리고 어떤 경우든 **유전체(genome)가 `@reviewer`·`@fact-checker`를 이미 상속**하므로, 새 QA 에이전트를 처음부터 짜기 전에 상속된 자산을 먼저 본다.

---

## 목차

1. QA는 CYS에서 무엇으로 표현되는가 (메커니즘 매핑)
2. QA 에이전트가 놓치는 결함의 패턴 (경계면 불일치)
3. 통합 정합성 검증 (Integration Coherence Verification) — 교차 비교
4. verify-before-assert: QA는 예측한 실패를 재현해야 한다
5. 발견 트리아지 (severity / confidence / blocking / by-design)
6. QA를 graph.json에 박는 법 (reflect-then-revise vs producer-reviewer)
7. 상속된 QA 자산: @reviewer / @fact-checker
8. QA 노드의 모델 티어 (role→tier 정책)
9. 검증 체크리스트 템플릿
10. QA critic 에이전트 정의 템플릿
11. 실제 사례: SatangSlide 7개 버그

---

## 1. QA는 CYS에서 무엇으로 표현되는가 (메커니즘 매핑)

원본은 "QA 에이전트"라는 단일 개념을 `.claude/agents/qa-inspector.md`에 직접 작성하고, 팀 통신 프로토콜로 다른 에이전트에게 수정을 요청하게 했다. CYS에서 QA는 **계약(graph.json)에 먼저 표현**되고, 그 표현은 두 축으로 갈린다.

| 원본 개념 | CYS 대응 | 언제 쓰나 |
|----------|---------|----------|
| 같은 산출물을 만든 에이전트가 스스로 다시 검토·수정 | `decision_mechanism: reflect-then-revise` (critic 노드) | 생산과 비평의 컨텍스트가 같고, 수정 권한도 같은 노드에 있을 때 |
| 별도 QA 에이전트가 생산자 산출물을 검토하고 반려 → 생산자 재작업 | `topology: producer-reviewer` (bounded loop) | 검토자의 독립성·적대성이 중요하고, 생산/검토 책임을 분리해야 할 때 |
| QA가 여러 모듈 산출물을 한 번에 정합성 검사 | `dispatch` 싱크 노드 + `qa-scan` role, 또는 파이프라인 말단의 critic 노드 | 팬아웃 결과를 모아 경계면을 교차 비교할 때 |
| "팀 통신으로 즉시 수정 요청" | edges(ordering) + on_exhaust + max_rounds 로 표현 | 실시간 통신은 Mode-A에서 불가 → 라운드 기반 루프로 표현 |

**중요한 패러다임 차이**: 원본의 "팀 통신 프로토콜"(발견 즉시 해당 에이전트에게 알림)은 Mode-A workflow에서 **불가능**하다. 워크플로우는 결정론적으로 스케줄되며 노드 간 실시간 통신이 없다. 따라서 QA의 "반려 → 재작업" 루프는 **통신이 아니라 토폴로지**로 표현한다: `producer-reviewer`가 reviewer의 verdict를 producer의 다음 라운드 input으로 다시 넣고, `max_rounds`만큼 반복하며, 소진 시 `on_exhaust`로 종료한다. 실시간 상호 비평이 진짜로 본질적인 경우에만 Mode-B(team)로 폴백한다 — 그러나 QA의 99%는 라운드 루프로 충분하다.

---

## 2. QA 에이전트가 놓치는 결함의 패턴 (경계면 불일치)

이 절은 패러다임과 무관한 금(金)이다. 그대로 보존한다.

### 2-1. 경계면 불일치 (Boundary Mismatch)

가장 빈번한 결함. 두 컴포넌트가 각각 "올바르게" 구현되어 있지만, 연결 지점에서 계약이 어긋남.

| 경계면 | 불일치 예시 | 놓치는 이유 |
|--------|-----------|-----------|
| API 응답 → 프론트 훅 | API가 `{ projects: [...] }` 반환, 훅이 `SlideProject[]` 기대 | 각각 개별 검증하면 정상, 교차 비교 안 함 |
| API 응답 필드명 → 타입 정의 | API가 `thumbnailUrl`(camelCase), 타입이 `thumbnail_url`(snake_case) | TypeScript 제네릭으로 캐스팅하면 컴파일러가 못 잡음 |
| 파일 경로 → 링크 href | 페이지가 `/dashboard/create`에 있는데 링크가 `/create`로 지정 | 파일 구조와 href를 교차 비교하지 않음 |
| 상태 전이 맵 → 실제 status 업데이트 | 맵에 `generating_template → template_approved` 정의, 코드에서 전환 누락 | 맵 존재 확인만 하고, 모든 업데이트 코드를 추적하지 않음 |
| API 엔드포인트 → 프론트 훅 | API 존재하지만 대응 훅 없음 (호출 안 됨) | API 목록과 훅 목록을 1:1 매핑하지 않음 |
| 즉시 응답 → 비동기 결과 | API가 즉시 `{ status }` 반환, 프론트가 `data.failedIndices` 접근 | 동기/비동기 응답 구분 없이 타입만 확인 |

**CYS 일반화**: 이 "경계면"은 graph.json에서 **edge가 잇는 두 노드의 계약 불일치**로 그대로 나타난다. node A의 `output_schema`(생산자 계약)와 node B의 `inputs`가 기대하는 shape(소비자 계약)이 어긋나면, 각각은 자기 `output_schema`를 통과해도 연결 지점에서 깨진다. QA critic 노드가 검증해야 할 1순위는 바로 **인접 노드 간 output_schema ↔ inputs 정합성**이다. (`validate_harness.py`는 edge 무결성·스키마 파일 존재는 잡지만, "A의 출력 shape이 B의 기대와 의미적으로 맞는가"는 정적 검사로 잡을 수 없다 — 그래서 QA 노드가 필요하다.)

### 2-2. 왜 정적 검사로 못 잡나

- **TypeScript 제네릭의 한계**: `fetchJson<SlideProject[]>()` — 런타임 응답이 `{ projects: [...] }`여도 컴파일 통과.
- **`npm run build` 통과 ≠ 정상 동작**: 타입 캐스팅, `any`, 제네릭이 사용되면 빌드는 성공하지만 런타임에 실패.
- **존재 검증 vs 연결 검증의 차이**: "API가 있는가?"와 "API의 응답이 호출측의 기대와 일치하는가?"는 전혀 다른 검증.
- **CYS 추가**: `validate_harness.py`의 머신체크 세트(스키마, agent-file-exists, edge integrity, cycle, write-path overlap, schema-file-exists 등)는 **구조적 정적 게이트**다. 이건 "노드가 존재하는가, 연결이 무결한가"를 잡는다. 하지만 "노드 A가 실제로 생산한 산출물이 노드 B가 의미적으로 쓸 수 있는가"는 잡지 못한다. 즉 **validate_harness.py = 빌드 게이트(구조), QA critic 노드 = 의미 게이트(런타임 정합성)**. 둘은 보완재이지 대체재가 아니다.

---

## 3. 통합 정합성 검증 (Integration Coherence Verification) — 교차 비교

QA critic/reviewer 노드에 반드시 포함해야 하는 **교차 비교 검증** 영역. 원본의 4개 검증 절차를 그대로 보존하되, CYS에서는 이 절차들이 **critic 에이전트 프롬프트의 검증 프로토콜**로 들어간다.

### 3-1. API 응답 ↔ 프론트 훅 타입 교차 검증

**방법**: 각 API route의 `NextResponse.json()` 호출부와 대응 훅의 `fetchJson<T>` 타입 파라미터를 비교.

```
검증 단계:
1. API route에서 NextResponse.json()에 전달하는 객체의 shape 추출
2. 대응 훅에서 fetchJson<T>의 T 타입 확인
3. shape과 T가 일치하는지 비교
4. 래핑 여부 확인 (API가 { data: [...] }를 반환하면 훅이 .data를 꺼내는지)
```

**특히 주의할 패턴:**
- 페이지네이션 API: `{ items: [], total, page }` vs 프론트가 배열 기대
- snake_case DB 필드 → camelCase API 응답 → 프론트 타입 정의 간 불일치
- 즉시 응답 (202 Accepted) vs 최종 결과의 shape 차이

### 3-2. 파일 경로 ↔ 링크/라우터 경로 매핑

**방법**: `src/app/` 하위 page 파일의 URL 경로를 추출하고, 코드 내 모든 `href`, `router.push()`, `redirect()` 값과 대조.

```
검증 단계:
1. src/app/ 하위 page.tsx 파일 경로에서 URL 패턴 추출
   - (group) → URL에서 제거
   - [param] → 동적 세그먼트
2. 코드 내 모든 href=, router.push(, redirect( 값 수집
3. 각 링크가 실제 존재하는 page 경로와 매칭되는지 확인
4. route group 내부 페이지의 URL 접두사 주의 (예: dashboard/ 하위)
```

### 3-3. 상태 전이 완전성 추적

**방법**: 코드에서 모든 `status:` 업데이트를 추출하여 상태 전이 맵과 대조.

```
검증 단계:
1. 상태 전이 맵(STATE_TRANSITIONS)에서 허용된 전이 목록 추출
2. 모든 API route에서 .update({ status: "..." }) 패턴 검색
3. 각 전이가 맵에 정의되어 있는지 확인
4. 맵에 정의된 전이 중 코드에서 실행되지 않는 것 식별 (죽은 전이)
5. 특히: 중간 상태(예: generating_template)에서 최종 상태(template_approved)로의 전환이 누락되지 않았는지
```

### 3-4. API 엔드포인트 ↔ 프론트 훅 1:1 매핑

**방법**: 모든 API route와 프론트 훅을 나열하여 짝이 맞는지 확인.

```
검증 단계:
1. src/app/api/ 하위 route.ts에서 HTTP 메서드별 엔드포인트 목록 추출
2. src/hooks/ 하위 use*.ts에서 fetch 호출 URL 목록 추출
3. API 엔드포인트 중 훅에서 호출하지 않는 것 식별 → "사용 안 됨" 플래그
4. "사용 안 됨"이 의도적인지 (관리 API 등) 아닌지 (호출 누락) 판단
```

### 3-5. "양쪽을 동시에 읽어라" 원칙 (보존)

QA가 경계면 버그를 잡으려면 한쪽만 읽어선 안 된다. 반드시:
- API route **와** 대응 훅을 **같이** 읽고
- 상태 전이 맵 **와** 실제 업데이트 코드를 **같이** 읽고
- 파일 구조 **와** 링크 경로를 **같이** 읽어야 한다.

CYS에서 이건 critic 노드의 `inputs[]`에 **양쪽 산출물을 모두 선언**하는 것으로 강제된다. critic이 생산자 한 노드의 output만 input으로 받으면 경계면 비교가 구조적으로 불가능하다. 따라서 정합성 검증 critic 노드는 **반드시 비교 대상 양쪽을 inputs에 명시**하라 — 이것이 원본의 "양쪽 동시 읽기"를 계약 차원에서 보장하는 방법이다.

| 검증 대상 | 왼쪽 (생산자) | 오른쪽 (소비자) |
|----------|-------------|---------------|
| API 응답 shape | route.ts의 NextResponse.json() | hooks/의 fetchJson<T> |
| 라우팅 | src/app/ page 파일 경로 | href, router.push 값 |
| 상태 전이 | STATE_TRANSITIONS 맵 | .update({ status }) 코드 |
| DB → API → UI | 테이블 컬럼명 | API 응답 필드 → 타입 정의 |
| (CYS) 노드 경계면 | node A의 output_schema | node B의 inputs 기대 shape |

---

## 4. verify-before-assert: QA는 예측한 실패를 재현해야 한다

원본 가이드는 정적 교차 비교에 머물렀다. CYS는 한 단계 더 요구한다: **QA가 "여기 버그가 있다"고 단언하려면, 정적으로 읽기만 해선 안 되고 예측한 실패를 실제로 재현해야 한다.**

이유: 정적 교차 비교는 false positive를 많이 낸다. "타입이 안 맞아 보인다"가 실제로는 어딘가의 변환 레이어로 해소되는 경우가 흔하다. 적대적 reviewer가 매 라운드 의심을 던지면(상속된 `@reviewer`는 "최소 1개 이슈"가 강제됨), 재현 단계가 없으면 노이즈가 누적되어 producer-reviewer 루프가 헛돈다.

**verify-before-assert 프로토콜** (critic/reviewer 노드 프롬프트에 명시):

```
하나의 경계면 버그를 단언하기 전에:
1. PREDICT — 정적으로 어떤 입력/경로에서 무엇이 깨지는지 구체적으로 예측한다.
   예: "projects 페이지 로드 시 projects.filter가 호출되는데, API는 객체를 반환하므로 TypeError."
2. REPRODUCE — 그 예측을 재현 가능한 형태로 확정한다:
   - 코드 실행 가능: 최소 재현 스니펫/테스트로 실제 에러를 띄운다.
   - 실행 불가(설계 산출물): 양쪽 계약(output_schema vs inputs)을 나란히 인용하고,
     "A는 X를 내고 B는 Y를 기대 → 불일치"를 라인 단위로 증거로 제시한다.
3. ASSERT — 재현/증거가 확보된 것만 finding으로 올린다. "그래 보인다"는 올리지 않는다.
```

이것은 상속된 `@fact-checker`의 "claim-by-claim, 독립 출처로 검증" DNA를 코드 정합성 도메인으로 옮긴 것이다: **모든 finding은 "재현/증거 없음 → 확정 보류"가 기본값**이다. 재현 가능 여부는 critic 노드의 model 선택에도 영향을 준다(§8).

---

## 5. 발견 트리아지 (severity / confidence / blocking / by-design)

원본은 "발견 즉시 수정 요청"이었다. CYS의 producer-reviewer 루프는 **반려/통과 결정이 결정론적이어야** 하므로, reviewer의 finding은 자유 서술이 아니라 **구조화된 트리아지**로 출력되어 critic 노드의 `output_schema`(권장: `schemas/critique.json`, reflect-then-revise 노드는 이 스키마가 사실상 필수)를 채운다.

각 finding은 4개 축을 갖는다:

| 축 | 값 | 의미 |
|----|----|----|
| `severity` | critical / major / minor | 영향 크기. critical=런타임 크래시/데이터 손상, major=핵심 기능 오동작, minor=품질·명명. |
| `confidence` | reproduced / evidenced / suspected | §4 verify-before-assert 결과. reproduced=실제 재현, evidenced=양쪽 계약 라인 인용, suspected=정적 의심(블로킹 불가). |
| `blocking` | true / false | 이 라운드를 반려시키는가. 규칙: `blocking = (severity ∈ {critical,major}) AND (confidence ∈ {reproduced,evidenced})`. |
| `by_design` | true / false | 의도된 동작인가(예: 관리 전용 API라 훅 없음). by_design=true면 finding이 아니라 주석으로 강등. |

**루프 종료 규칙**(producer-reviewer 토폴로지):
- reviewer가 `blocking=true` finding을 0개 내면 → 통과(루프 종료).
- `blocking=true`가 1개 이상이면 → 그 findings를 producer의 다음 라운드 inputs로 주입, 라운드 +1.
- `max_rounds` 도달 시 → node의 `on_exhaust`로 처리:
  - `proceed-with-gap`: 남은 finding을 known-gap으로 기록하고 진행(비치명적 산출물).
  - `escalate`: 사람/상위 노드에게 에스컬레이션(치명적 산출물의 기본값).
  - `force-pass`: 거의 쓰지 않음 — QA를 형식적으로 통과시키는 안티패턴. 명시적 정당화 없이 쓰지 말 것.

`suspected`(정적 의심)는 **블로킹할 수 없다.** 이것이 §4와 §5를 잇는 핵심: 재현/증거 없는 의심으로 루프를 반려시키면 false positive가 무한 라운드를 유발한다. suspected는 다음 라운드에 "재현해보라"는 과제로만 전달된다.

---

## 6. QA를 graph.json에 박는 법 (reflect-then-revise vs producer-reviewer)

QA를 계약에 표현하는 두 가지 정석. 무엇을 고를지는 **독립성 요구**와 **컨텍스트 공유**로 결정한다.

### 6-1. reflect-then-revise (critic 노드, 단일 노드 내 자기비평)

한 노드가 산출 → 같은 노드의 critic이 비평 → 같은 에이전트가 수정. 생산과 비평의 컨텍스트가 동일하고, 수정 권한이 생산자에게 있을 때.

```json
{
  "id": "draft_report",
  "agent": "report-writer",
  "model": "sonnet",
  "decision_mechanism": "reflect-then-revise",
  "mechanism_params": { "max_rounds": 2, "critic": "opus" },
  "inputs": ["sources.json", "outline.json"],
  "outputs": ["report.md"],
  "write_paths": ["/abs/out/report.md"],
  "output_schema": "schemas/report.json",
  "retries": 1,
  "on_exhaust": "proceed-with-gap",
  "max_rounds": 2
}
```

- `critic` 티어는 별도 지정(여기 opus): 생산자(reviser)는 sonnet, 비평자는 opus가 정석(§8).
- critique는 `schemas/critique.json`을 채운다(§5의 4축 finding). emitter가 critic 라운드를 자동 배선한다.
- **장점**: 가볍다(노드 1개). **한계**: 같은 컨텍스트라 적대성·독립성이 약하다 — 자기 가정을 자기가 못 의심하는 blind spot. 경계면 정합성처럼 **독립적 시선이 본질인 QA에는 부적합**.

### 6-2. producer-reviewer (토폴로지, 생산/검토 분리)

생산자 노드와 검토자 노드를 분리하고 bounded loop를 돈다. 검토자의 **독립성·적대성**이 중요하고, 경계면 교차 비교처럼 양쪽 산출물을 함께 봐야 할 때 — 즉 §2~§3의 통합 정합성 검증의 정석.

```json
{
  "schema_version": "0.1",
  "harness_name": "feature-build",
  "topology": "producer-reviewer",
  "nodes": [
    {
      "id": "build_api",
      "agent": "backend-builder", "model": "sonnet",
      "decision_mechanism": "single", "mechanism_params": {},
      "inputs": ["spec.json"], "outputs": ["api/route.ts"],
      "write_paths": ["/abs/src/app/api"], "output_schema": "schemas/api.json",
      "retries": 1, "on_exhaust": "escalate", "max_rounds": 1
    },
    {
      "id": "build_hook",
      "agent": "frontend-builder", "model": "sonnet",
      "decision_mechanism": "single", "mechanism_params": {},
      "inputs": ["spec.json", "api/route.ts"], "outputs": ["hooks/useX.ts"],
      "write_paths": ["/abs/src/hooks"], "output_schema": "schemas/hook.json",
      "retries": 1, "on_exhaust": "escalate", "max_rounds": 1
    },
    {
      "id": "qa_coherence",
      "agent": "qa-coherence-reviewer", "model": "opus",
      "decision_mechanism": "single", "mechanism_params": {},
      "inputs": ["api/route.ts", "hooks/useX.ts", "spec.json"],
      "outputs": ["critique.json"],
      "write_paths": ["/abs/out/qa"], "output_schema": "schemas/critique.json",
      "retries": 0, "on_exhaust": "escalate", "max_rounds": 3
    }
  ],
  "edges": [
    { "from": "build_api", "to": "build_hook" },
    { "from": "build_hook", "to": "qa_coherence" },
    { "from": "qa_coherence", "to": "build_hook" }
  ]
}
```

- **`qa_coherence`의 inputs에 양쪽(`api/route.ts`, `hooks/useX.ts`)을 모두 선언** — §3-5 "양쪽 동시 읽기"를 계약으로 강제.
- 마지막 edge `qa_coherence → build_hook`이 **반려 루프**다. reviewer가 blocking finding을 내면 producer가 그 finding을 input으로 재작업. edge는 ordering일 뿐 depends_on이 아니므로, 루프는 토폴로지(`producer-reviewer`)와 `max_rounds`가 해석한다.
- `on_exhaust: escalate` — 경계면 버그가 max_rounds 내 안 잡히면 묻어가지 말고 올린다.

### 6-3. incremental QA 원칙 (보존 + CYS 표현)

원본: "QA를 전체 완성 후가 아니라 각 모듈 완성 직후 실행하라." CYS에서 이건 **QA 노드를 파이프라인 말단 하나로 몰지 말고, 각 모듈 산출 직후에 producer-reviewer 루프를 배치**하는 것으로 표현된다. 버그 누적·전파를 막는다. 단, 전역 경계면(여러 모듈을 가로지르는 정합성)은 `dispatch`의 싱크 노드 또는 파이프라인 말단 critic으로 한 번 더 검사한다 — incremental(국소) + final(전역)의 2단.

---

## 7. 상속된 QA 자산: @reviewer / @fact-checker

새 QA 에이전트를 짜기 전에, **유전체가 이미 상속한 적대적 QA 에이전트**를 먼저 본다. `inherit_genome.py`가 자식 하네스에 `.claude/agents/reviewer.md`, `.claude/agents/fact-checker.md`를 그대로 넣는다.

| 상속 에이전트 | DNA | 역할 | 모델 | 권한 |
|--------------|-----|------|------|------|
| `@reviewer` | AgenticWorkflow Generator-Critic gene | 적대적 코드/산출물 리뷰. pre-mortem 필수, **최소 1개 이슈** 강제, 독립 pACS 채점 | opus | read-only (Read/Glob/Grep) |
| `@fact-checker` | P1 gene("코드는 거짓말 안 한다") | claim-by-claim 사실 검증, **인용된 출처 말고 독립 출처로 교차검증** | opus | Read/Glob/Grep + WebSearch/WebFetch |

**활용 규칙**:
- 산출물이 **코드/구조 정합성**이면 → `@reviewer`를 producer-reviewer의 reviewer 노드 agent로 직접 지정하거나, 그 프로토콜(pre-mortem, 최소 1이슈, read-only)을 도메인 critic의 베이스로 삼는다.
- 산출물이 **사실 주장(리서치/리포트)**이면 → `@fact-checker`를 critic으로. §4 verify-before-assert는 이 에이전트의 "독립 출처 교차검증" DNA를 코드 도메인으로 일반화한 것이다.
- **새로 짜야 하는 경우**: 경계면 교차 비교(§3)처럼 도메인 특화 검증 절차가 필요할 때만. 이때도 상속 에이전트의 적대성·read-only·구조화 출력 원칙을 그대로 따른다.
- `@reviewer`는 read-only다 — **수정 권한이 없다.** 그래서 producer-reviewer에서 reviewer는 finding만 내고, 수정은 반드시 producer 노드가 한다. (reflect-then-revise에서는 reviser가 수정.) write_paths를 critic 노드에 주지 마라.

---

## 8. QA 노드의 모델 티어 (role→tier 정책)

원본은 "QA 에이전트는 general-purpose 타입"이라고만 했다(읽기+grep+스크립트 필요). CYS는 모델 티어를 `model-tier-policy.js`로 강제한다. QA 안에서도 역할에 따라 티어가 갈린다 — **"모든 QA가 opus"는 안티패턴이고, "모든 QA가 haiku"도 안티패턴이다.**

| QA 하위 역할 | role-class | model | 근거 |
|-------------|-----------|-------|------|
| 기계적 스캔(lint, grep 패턴 추출, 존재 확인) | `qa-scan` | **haiku** | 정해진 패턴 추출·대조. 추론 없음. 싸게. |
| producer-reviewer의 producer(재작업) | `reviser` | **sonnet** | 고정 프레임 안의 bounded 수정. |
| 경계면 정합성 비평 / 적대적 리뷰 | `critic` | **opus** | 개방형 의심·가정 깨기. 자기비평의 blind spot을 넘으려면 최상위 추론 필요. |
| 사실 검증 판정(verdict) | `judge`/`critic` | **opus** | 최종 판정. |

- 모든 노드는 `model:`(필수) + agent frontmatter에 `model_rationale:`(필수)을 가져야 한다. `validate_harness.py`의 V1이 누락을 잡는다(M0: rationale 누락은 warn, model 누락은 error).
- **V2 규칙 주의**: `qa-scan` role-class에 opus를 쓰면 V2(TIER_OVERSPEND)가 error를 낸다. 단순 스캔은 haiku로. 정말 opus가 필요하면 `tier_override_reason`을 명시(그러면 warn으로 강등).
- **티어 선택 휴리스틱**: "이 QA가 정해진 패턴을 기계적으로 대조하는가(→haiku) vs 가정을 의심하고 경계면의 숨은 불일치를 추론으로 찾아내는가(→opus)?" 경계면 교차 비교(§3)와 verify-before-assert의 PREDICT 단계(§4)는 본질적으로 추론이므로 **opus**다. 그 안의 grep 추출만 떼어 별도 `qa-scan` 노드로 만들면 haiku로 내릴 수 있다(비용 최적화 패턴).

---

## 9. 검증 체크리스트 템플릿

QA critic/reviewer 노드의 프롬프트(에이전트 파일 본문)에 포함할 웹 애플리케이션용 통합 정합성 체크리스트. 원본을 보존하되, 각 항목은 §5의 4축 finding으로 출력되어야 함을 전제한다.

```markdown
### 통합 정합성 검증 (웹 앱) — 각 항목 위반 시 §5 4축 finding 발행

#### API ↔ 프론트엔드 연결
- [ ] 모든 API route의 응답 shape과 대응 훅의 제네릭 타입이 일치
- [ ] 래핑된 응답({ items: [...] })은 훅에서 unwrap하는지 확인
- [ ] snake_case ↔ camelCase 변환이 일관되게 적용
- [ ] 즉시 응답(202)과 최종 결과의 shape이 프론트에서 구분되는지 확인
- [ ] 모든 API 엔드포인트에 대응하는 프론트 훅이 존재하고 실제로 호출됨

#### 라우팅 정합성
- [ ] 코드 내 모든 href/router.push 값이 실제 page 파일 경로와 매칭
- [ ] route group ((group))이 URL에서 제거되는 것을 고려한 경로 검증
- [ ] 동적 세그먼트([id])가 올바른 파라미터로 채워지는지 확인

#### 상태 머신 정합성
- [ ] 정의된 모든 상태 전이가 코드에서 실행됨 (죽은 전이 없음)
- [ ] 코드의 모든 status 업데이트가 전이 맵에 정의됨 (무단 전이 없음)
- [ ] 중간 상태에서 최종 상태로의 전환이 누락되지 않음
- [ ] 프론트에서 상태 기반 분기(if status === "X")의 X가 실제 도달 가능

#### 데이터 흐름 정합성
- [ ] DB 스키마 필드명과 API 응답 필드명의 매핑이 일관됨
- [ ] 프론트 타입 정의와 API 응답의 필드명이 일치
- [ ] 옵셔널 필드에 대한 null/undefined 처리가 양쪽에서 일관됨

#### (CYS) 하네스 경계면 정합성 — graph.json 산출물 자체를 QA할 때
- [ ] 인접 노드 A.output_schema와 B.inputs 기대 shape이 의미적으로 일치
- [ ] producer-reviewer 반려 edge가 실제로 producer로 되돌아가는가
- [ ] critic 노드 inputs에 비교 대상 "양쪽"이 모두 선언됨
- [ ] 모든 finding이 verify-before-assert를 통과(suspected는 비블로킹)
```

---

## 10. QA critic 에이전트 정의 템플릿

producer-reviewer의 reviewer 노드(또는 reflect-then-revise의 critic)로 쓸 도메인 QA 에이전트. 상속된 `@reviewer` 프로토콜을 베이스로 한다. **frontmatter에 model + model_rationale 필수, read-only.**

```markdown
---
name: qa-coherence-reviewer
description: "통합 정합성 적대적 검토자. 경계면 불일치를 양쪽 동시 읽기 + verify-before-assert로 잡고, 4축 트리아지 finding을 발행."
model: opus
model_rationale: "경계면 불일치는 정해진 패턴이 아니라 숨은 가정의 어긋남이다. 가정을 의심하고 교차 비교로 추론하는 개방형 비평이므로 critic role-class → opus."
tools: Read, Glob, Grep
---

# QA Coherence Reviewer

## 핵심 정체
나는 검증자가 아니라 비평가다. 옳음을 확인하는 게 아니라 무엇이 틀렸는지 찾는다.
이슈를 못 찾았다면 충분히 들여다보지 않은 것이다. (상속 @reviewer DNA)

## 검증 우선순위
1. 통합 정합성 (가장 높음) — 경계면 불일치가 런타임 에러의 주된 원인
2. 기능 스펙 준수 — API/상태머신/데이터모델
3. 디자인 품질 — 색상/타이포/반응형
4. 코드 품질 — 미사용 코드, 명명 규칙

## 검증 방법: "양쪽 동시 읽기" (inputs에 양쪽이 선언되어 있다)
| 검증 대상 | 왼쪽 (생산자) | 오른쪽 (소비자) |
|----------|-------------|---------------|
| API 응답 shape | route.ts의 NextResponse.json() | hooks/의 fetchJson<T> |
| 라우팅 | src/app/ page 파일 경로 | href, router.push 값 |
| 상태 전이 | STATE_TRANSITIONS 맵 | .update({ status }) 코드 |
| DB → API → UI | 테이블 컬럼명 | API 응답 필드 → 타입 정의 |

## verify-before-assert (모든 finding 의무)
1. PREDICT: 어떤 입력/경로에서 무엇이 깨지는지 구체적으로 예측.
2. REPRODUCE: 재현(스니펫/테스트) 또는 양쪽 계약 라인 인용으로 증거 확보.
3. ASSERT: 재현/증거 확보된 것만 finding. "그래 보인다"는 suspected로만.

## 출력: 4축 트리아지 finding (schemas/critique.json)
각 finding = { severity: critical|major|minor,
               confidence: reproduced|evidenced|suspected,
               blocking: bool,   # (critical|major) AND (reproduced|evidenced)
               by_design: bool,
               location: "file:line", evidence: "...", fix_suggestion: "..." }
blocking finding이 0이면 PASS, 1+이면 producer로 반려(다음 라운드 input).

## 절대 규칙
- read-only. write/edit/bash 없음. 수정은 producer 노드가 한다.
- 최소 1개 이슈(상속 P1 layer가 zero-issue 리뷰를 거부).
- suspected는 블로킹 금지(false positive가 루프를 헛돌게 함).
```

---

## 11. 실제 사례: SatangSlide 7개 버그 (보존)

이 가이드의 모든 내용은 아래 실제 버그에서 추출한 교훈이다. 각 버그가 어떤 CYS 메커니즘으로 잡혔어야 하는지 함께 적는다.

| 버그 | 경계면 | 원인 | CYS에서 잡는 법 |
|------|--------|------|----------------|
| `projects?.filter is not a function` | API→훅 | API가 `{projects:[]}` 반환, 훅이 배열 기대 | critic inputs에 양쪽 선언 + reproduced 등급 finding |
| 대시보드 모든 링크 404 | 파일경로→href | `/dashboard/` 접두사 누락 | 라우팅 정합성 체크 + 경로 교차 대조 |
| 테마 이미지 안 보임 | API→컴포넌트 | `thumbnailUrl` vs `thumbnail_url` | 데이터 흐름 정합성(필드명 매핑) |
| 테마 선택 저장 안 됨 | API→훅 | select-theme API 존재, 훅 없음 | API↔훅 1:1 매핑(미호출 식별) |
| 생성 페이지 영원히 대기 | 상태전이→코드 | `template_approved` 전이 코드 누락 | 상태 머신 정합성(죽은 전이 추적) |
| `data.failedIndices` 크래시 | 즉시응답→프론트 | 백그라운드 결과를 즉시 응답에서 접근 | 동기/비동기 shape 구분 + verify-before-assert |
| 완료 후 슬라이드 보기 404 | 파일경로→href | `/projects/` → `/dashboard/projects/` | 라우팅 정합성 + route group 접두사 |

**핵심 교훈(불변)**: 7개 중 6개가 **경계면 불일치**다. 단일 노드 자기검증(reflect-then-revise)으로는 이 중 대부분을 못 잡는다 — 양쪽을 함께 보는 독립 검토(producer-reviewer)와, 의심을 재현으로 확정하는 verify-before-assert가 있어야 비로소 잡힌다. 그리고 이 QA는 빌드 게이트(`validate_harness.py`)가 아니라 **런타임 정합성을 보는 의미 게이트**다 — 둘 다 있어야 한다.

---

## 부록: 진화 / 피드백 루프

QA 하네스도 산출물이다. 운영 중 잡히지 않고 새어나간 경계면 버그가 있으면:
1. 그 버그의 경계면 유형을 §2 표에 추가.
2. critic 에이전트의 체크리스트(§9)에 해당 항목 추가.
3. 재현 가능했는데 못 잡았으면 → verify-before-assert PREDICT 단계의 누락. confidence 등급 기준 보강.
4. false positive로 루프가 헛돌았으면 → suspected 비블로킹 규칙(§5) 또는 model 티어(§8) 점검.

이 피드백 루프는 `lift_gate.py`(with-skill vs haiku-baseline)로 측정 가능하다 — QA를 추가한 하네스가 baseline 대비 실제로 더 많은 진짜 버그를 잡는지, 독립 블라인드 채점으로 검증하라. 못 잡으면 QA 노드를 추가한 토큰 비용이 정당화되지 않는다.
