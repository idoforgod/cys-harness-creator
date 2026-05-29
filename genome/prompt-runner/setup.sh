#!/bin/bash
# ═══════════════════════════════════════════════════════════════
#  setup.sh — 프롬프트 자동 실행 셋업 템플릿
#
#  사용법:
#    1. 아래 2개 변수를 채운다
#    2. 터미널에서 bash setup.sh 실행
#    3. python3 run.py 실행
# ═══════════════════════════════════════════════════════════════

# ┌─────────────────────────────────────────────────────────────┐
# │  여기에 2가지를 채우세요                                      │
# └─────────────────────────────────────────────────────────────┘

# ① 무엇을 만들 것인가 (제목/한 줄 설명)
PROJECT_TITLE="여기에_만들_서비스_제목을_적으세요"

# ② 최종 결과물의 수준과 형태 (목표)
PROJECT_GOAL="여기에_최종_결과물의_수준과_형태를_적으세요"

# ┌─────────────────────────────────────────────────────────────┐
# │  작성 예시                                                    │
# ├─────────────────────────────────────────────────────────────┤
# │                                                              │
# │  PROJECT_TITLE="한국 교회 미래 예측 시뮬레이션 시스템"            │
# │                                                              │
# │  PROJECT_GOAL="2025-2045년 한국 교회 인구, 재정, 목회 트렌드를   │
# │  빅데이터와 AI 에이전트로 분석하여, 전문 연구자 수준의 미래        │
# │  시나리오 보고서(한국어+영어)를 자동 생성하는 것"                  │
# │                                                              │
# └─────────────────────────────────────────────────────────────┘


# ═══════════════════════════════════════════════════════════════
#  아래부터는 수정하지 마세요
# ═══════════════════════════════════════════════════════════════

set -uo pipefail  # -e 제거: grep 0 결과 시 exit code 1 문제 방지

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPTS_DIR="${SCRIPT_DIR}/prompts"

# 입력 검증
if [[ "$PROJECT_TITLE" == *"서비스_제목을_적으세요"* ]] || [[ -z "$PROJECT_TITLE" ]]; then
    echo "❌ 오류: PROJECT_TITLE을 채워주세요."
    echo "   setup.sh 파일을 열어서 2가지 변수를 채운 후 다시 실행하세요."
    exit 1
fi

if [[ "$PROJECT_GOAL" == *"수준과_형태를_적으세요"* ]] || [[ -z "$PROJECT_GOAL" ]]; then
    echo "❌ 오류: PROJECT_GOAL을 채워주세요."
    echo "   setup.sh 파일을 열어서 2가지 변수를 채운 후 다시 실행하세요."
    exit 1
fi

echo "═══════════════════════════════════════════════════════"
echo "  프롬프트 플레이스홀더 치환 시작"
echo "═══════════════════════════════════════════════════════"
echo ""
echo "  ① 프로젝트: $PROJECT_TITLE"
echo "  ② 목표:     $PROJECT_GOAL"
echo ""

# OS 감지 (macOS vs Linux의 sed 차이)
if [[ "$(uname)" == "Darwin" ]]; then
    SED_CMD="sed -i ''"
else
    SED_CMD="sed -i"
fi

# 치환 전 잔여 수 확인
BEFORE_1=$(grep -rl '여기에 만들기 원하는 것 입력' "$PROMPTS_DIR"/*.txt 2>/dev/null | wc -l | tr -d ' ')
BEFORE_2=$(grep -rl '여기에 내가 이 서비스를 만드는 가장 중요한 목적' "$PROMPTS_DIR"/*.txt 2>/dev/null | wc -l | tr -d ' ')

echo "  치환 전:"
echo "    플레이스홀더①: ${BEFORE_1}개 파일에 존재"
echo "    플레이스홀더②: ${BEFORE_2}개 파일에 존재"
echo ""

# ── 치환 실행 ──

# 플레이스홀더 ① 치환 (14개 파일)
# 원문: [ 여기에 만들기 원하는 것 입력 ]
cd "$PROMPTS_DIR"

# sed 특수문자 이스케이프 처리
ESCAPED_TITLE=$(printf '%s' "$PROJECT_TITLE" | sed 's/[&/\]/\\&/g')
ESCAPED_GOAL=$(printf '%s' "$PROJECT_GOAL" | sed 's/[&/\]/\\&/g')

if [[ "$(uname)" == "Darwin" ]]; then
    sed -i '' "s/\[ 여기에 만들기 원하는 것 입력 \]/${ESCAPED_TITLE}/g" *.txt
    sed -i '' "s/( 여기에 내가 이 서비스를 만드는 가장 중요한 목적, 혹은 결과물의 모양과 수준을 적는다 )/${ESCAPED_GOAL}/g" *.txt
else
    sed -i "s/\[ 여기에 만들기 원하는 것 입력 \]/${ESCAPED_TITLE}/g" *.txt
    sed -i "s/( 여기에 내가 이 서비스를 만드는 가장 중요한 목적, 혹은 결과물의 모양과 수준을 적는다 )/${ESCAPED_GOAL}/g" *.txt
fi

# 치환 후 잔여 수 확인 (grep가 0 결과일 때 exit 1 반환하므로 || true 추가)
AFTER_1=$(grep -rl '여기에 만들기 원하는 것 입력' "$PROMPTS_DIR"/*.txt 2>/dev/null | wc -l || true)
AFTER_1=$(echo "$AFTER_1" | tr -d '[:space:]')
AFTER_2=$(grep -rl '여기에 내가 이 서비스를 만드는 가장 중요한 목적' "$PROMPTS_DIR"/*.txt 2>/dev/null | wc -l || true)
AFTER_2=$(echo "$AFTER_2" | tr -d '[:space:]')

# 빈 값 처리
AFTER_1=${AFTER_1:-0}
AFTER_2=${AFTER_2:-0}

echo "  치환 후:"
echo "    플레이스홀더①: ${AFTER_1}개 잔여"
echo "    플레이스홀더②: ${AFTER_2}개 잔여"
echo ""

# 검증
if [[ "$AFTER_1" -eq 0 ]] && [[ "$AFTER_2" -eq 0 ]]; then
    echo "  ✅ 모든 플레이스홀더 치환 완료"
    echo ""
    echo "═══════════════════════════════════════════════════════"
    echo "  다음 단계:"
    echo "    1. python3 ${SCRIPT_DIR}/run.py --verify"
    echo "    2. python3 ${SCRIPT_DIR}/run.py --dry-run"
    echo ""
    echo "  ★ 실행 (프로젝트 루트 디렉토리를 반드시 지정하세요)"
    echo "    python3 ${SCRIPT_DIR}/run.py \\"
    echo "      --project-dir /path/to/your/project \\"
    echo "      --model claude-opus-4-5 \\"
    echo "      --skip-permissions \\"
    echo "      --max-turns 1000 \\"
    echo "      --timeout 7200"
    echo ""
    echo "  ※ --project-dir: Claude Code가 .claude/ 폴더를 찾는 기준 경로"
    echo "     hooks, commands, skills, CLAUDE.md 가 이 경로 기준으로 로드됩니다."
    echo "     미지정 시 run.py 실행 위치 기준 (보통 잘못된 경로가 됩니다)"
    echo "  ※ --model: agent-swarm 작업에는 opus 모델 강력 권장"
    echo "     미지정 시 Claude Code 기본값(Sonnet)이 사용되어 품질 저하 가능"
    echo "═══════════════════════════════════════════════════════"
else
    echo "  ❌ 치환 실패: 플레이스홀더가 남아있습니다."
    echo "    PROJECT_TITLE이나 PROJECT_GOAL에 sed 특수문자(/, &, \\)가"
    echo "    포함되어 있을 수 있습니다. 수동으로 치환해 주세요."
    exit 1
fi
