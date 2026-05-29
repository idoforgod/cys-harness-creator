#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════
  prompt_extractor.py — 결정론적 프롬프트 추출기
  
  목적: LLM의 확률적 동작을 원천 봉쇄하고,
        파이썬 코드로 100% 기계적으로 프롬프트를 추출/저장/검증
  
  사용법:
    python3 prompt_extractor.py extract   → 추출 + 저장 + 검증
    python3 prompt_extractor.py verify    → 기존 파일 검증만
    python3 prompt_extractor.py checksum  → MD5 체크섬 출력
═══════════════════════════════════════════════════════════════════
"""

import sys
import os
import re
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Tuple


# ─── 설정 ───────────────────────────────────────────────────────
ORIGINAL_FILE = None  # 실행 시 자동 탐색
PROMPTS_DIR = None    # 실행 시 자동 설정
MANIFEST_FILE = None


def find_original_file() -> str:
    """원본 마크다운 파일 자동 탐색"""
    candidates = [
        '/mnt/user-data/uploads/제목_없음_332e43a115c88019af63fba5c2fd8642.md',
        './source.md',
        './제목_없음_332e43a115c88019af63fba5c2fd8642.md',
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    # 현재 디렉토리에서 .md 파일 탐색
    for f in Path('.').glob('*.md'):
        if f.name not in ('ANALYSIS.md', 'README.md', 'CLAUDE.md'):
            return str(f)
    raise FileNotFoundError("원본 마크다운 파일을 찾을 수 없습니다.")


# ─── 핵심: 결정론적 코드 블록 추출기 ────────────────────────────
def extract_code_blocks(filepath: str) -> List[Dict]:
    """
    마크다운 파일에서 코드 블록을 기계적으로 추출합니다.
    
    규칙 (결정론적, 예외 없음):
    1. 4칸 들여쓰기 + ```json 또는 ```jsx 로 시작하는 라인 = 블록 시작
    2. 4칸 들여쓰기 + ``` 로만 구성된 라인 = 블록 종료
    3. 시작과 종료 사이의 모든 라인 = 블록 내용 (strip() 적용)
    4. 블록 번호는 1부터 시작, 발견 순서대로 연번
    """
    
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 패턴 정의 (컴파일된 정규식 — 결정론적)
    OPEN_PATTERN = re.compile(r'^    ```(json|jsx)\s*$')
    CLOSE_PATTERN = re.compile(r'^    ```\s*$')
    
    blocks: List[Dict] = []
    in_block = False
    block_content_lines: List[str] = []
    block_start_line = 0
    block_lang = ''
    
    for line_num_0based, line in enumerate(lines):
        line_num = line_num_0based + 1  # 1-based
        
        if not in_block:
            m = OPEN_PATTERN.match(line)
            if m:
                in_block = True
                block_lang = m.group(1)
                block_start_line = line_num
                block_content_lines = []
        else:
            # 종료 조건: ```만 있는 라인이면서, 시작 패턴이 아닌 것
            if CLOSE_PATTERN.match(line) and not OPEN_PATTERN.match(line):
                raw_content = ''.join(block_content_lines)
                stripped = raw_content.strip()
                
                md5 = hashlib.md5(stripped.encode('utf-8')).hexdigest()
                sha256 = hashlib.sha256(stripped.encode('utf-8')).hexdigest()
                
                blocks.append({
                    'index': len(blocks) + 1,
                    'start_line': block_start_line,
                    'end_line': line_num,
                    'language': block_lang,
                    'content': stripped,
                    'char_count': len(stripped),
                    'byte_count': len(stripped.encode('utf-8')),
                    'md5': md5,
                    'sha256': sha256,
                    'is_clear': stripped == '/clear',
                })
                in_block = False
            else:
                block_content_lines.append(line)
    
    # 안전장치: 닫히지 않은 블록 검사
    if in_block:
        raise RuntimeError(
            f"치명적 오류: 라인 {block_start_line}에서 시작된 코드 블록이 닫히지 않았습니다."
        )
    
    return blocks


# ─── 프롬프트 파일 저장 ──────────────────────────────────────────
def save_prompt_files(blocks: List[Dict], output_dir: str) -> None:
    """각 블록을 개별 텍스트 파일로 저장"""
    
    os.makedirs(output_dir, exist_ok=True)
    
    for block in blocks:
        filename = f"{block['index']:03d}.txt"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(block['content'])
    
    print(f"  ✅ {len(blocks)}개 프롬프트 파일 저장 완료 → {output_dir}/")


# ─── 매니페스트 생성 ─────────────────────────────────────────────
def save_manifest(blocks: List[Dict], filepath: str) -> None:
    """모든 블록의 메타데이터를 JSON으로 저장"""
    
    manifest = []
    for b in blocks:
        manifest.append({
            'file': f"{b['index']:03d}.txt",
            'index': b['index'],
            'start_line': b['start_line'],
            'end_line': b['end_line'],
            'language': b['language'],
            'is_clear': b['is_clear'],
            'char_count': b['char_count'],
            'byte_count': b['byte_count'],
            'md5': b['md5'],
            'sha256': b['sha256'],
        })
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    
    print(f"  ✅ 매니페스트 저장 완료 → {filepath}")


# ─── 검증: 저장된 파일과 원본 비교 ───────────────────────────────
def verify_files(blocks: List[Dict], prompts_dir: str) -> Tuple[int, int, List[str]]:
    """
    저장된 파일을 원본 블록과 바이트 단위로 비교합니다.
    
    Returns:
        (일치 수, 불일치 수, 오류 메시지 리스트)
    """
    
    matches = 0
    mismatches = 0
    errors: List[str] = []
    
    for block in blocks:
        filename = f"{block['index']:03d}.txt"
        filepath = os.path.join(prompts_dir, filename)
        
        # 파일 존재 확인
        if not os.path.exists(filepath):
            errors.append(f"#{block['index']:03d}: 파일 없음 ({filepath})")
            mismatches += 1
            continue
        
        # 파일 내용 읽기
        with open(filepath, 'r', encoding='utf-8') as f:
            saved_content = f.read()
        
        # 바이트 단위 비교
        original = block['content']
        
        if original == saved_content:
            # MD5도 이중 검증
            saved_md5 = hashlib.md5(saved_content.encode('utf-8')).hexdigest()
            if saved_md5 == block['md5']:
                matches += 1
            else:
                errors.append(
                    f"#{block['index']:03d}: 문자열 일치하나 MD5 불일치! "
                    f"(원본: {block['md5']}, 저장: {saved_md5})"
                )
                mismatches += 1
        else:
            # 차이점 상세 분석
            orig_bytes = len(original.encode('utf-8'))
            saved_bytes = len(saved_content.encode('utf-8'))
            saved_md5 = hashlib.md5(saved_content.encode('utf-8')).hexdigest()
            
            # 첫 번째 차이 위치 찾기
            first_diff = -1
            for j in range(min(len(original), len(saved_content))):
                if original[j] != saved_content[j]:
                    first_diff = j
                    break
            if first_diff == -1:
                first_diff = min(len(original), len(saved_content))
            
            errors.append(
                f"#{block['index']:03d}: 내용 불일치!\n"
                f"       원본: {orig_bytes} bytes, MD5: {block['md5']}\n"
                f"       저장: {saved_bytes} bytes, MD5: {saved_md5}\n"
                f"       첫 차이 위치: 문자 #{first_diff}\n"
                f"       원본[{first_diff}:+20]: {repr(original[first_diff:first_diff+20])}\n"
                f"       저장[{first_diff}:+20]: {repr(saved_content[first_diff:first_diff+20])}"
            )
            mismatches += 1
    
    # 여분 파일 검사
    expected = set(f"{b['index']:03d}.txt" for b in blocks)
    actual = set(f for f in os.listdir(prompts_dir) if f.endswith('.txt'))
    extra = actual - expected
    missing = expected - actual
    
    if extra:
        errors.append(f"여분 파일 발견: {sorted(extra)}")
    if missing:
        errors.append(f"누락 파일 발견: {sorted(missing)}")
    
    return matches, mismatches, errors


# ─── 전체 검증 보고서 출력 ────────────────────────────────────────
def print_verification_report(
    blocks: List[Dict], 
    matches: int, 
    mismatches: int, 
    errors: List[str]
) -> bool:
    """검증 결과를 출력하고 성공 여부를 반환"""
    
    total = len(blocks)
    clear_count = sum(1 for b in blocks if b['is_clear'])
    exec_count = total - clear_count
    
    print()
    print("=" * 70)
    print("  프롬프트 추출 검증 보고서")
    print("=" * 70)
    print()
    print(f"  총 코드 블록:    {total}개")
    print(f"    실행 프롬프트:  {exec_count}개")
    print(f"    /clear 명령:   {clear_count}개")
    print()
    print(f"  /clear 위치:     {[b['index'] for b in blocks if b['is_clear']]}")
    print()
    print(f"  검증 결과:")
    print(f"    ✅ 완벽 일치:  {matches}/{total}개")
    print(f"    ❌ 불일치:     {mismatches}/{total}개")
    print()
    
    if errors:
        print("  오류 상세:")
        for e in errors:
            for line in e.split('\n'):
                print(f"    {line}")
            print()
    
    if mismatches == 0 and matches == total:
        print("  ╔══════════════════════════════════════════════════╗")
        print(f"  ║  ✅ 검증 통과: {total}개 코드 블록                 ║")
        print("  ║     바이트 단위 100% 완벽 일치                  ║")
        print("  ║     MD5 체크섬 이중 검증 완료                   ║")
        print("  ╚══════════════════════════════════════════════════╝")
        print()
        return True
    else:
        print("  ╔══════════════════════════════════════════════════╗")
        print("  ║  ❌ 검증 실패: 불일치 발견                      ║")
        print("  ║     extract 명령으로 재추출 필요                ║")
        print("  ╚══════════════════════════════════════════════════╝")
        print()
        return False


# ─── 체크섬 출력 ──────────────────────────────────────────────────
def print_checksums(blocks: List[Dict]) -> None:
    """모든 블록의 체크섬을 출력 (외부 검증용)"""
    
    print()
    print("=" * 90)
    print(f"  {'#':>3}  {'MD5':>32}  {'Bytes':>6}  {'Lines':>10}  {'Type':<8}")
    print("=" * 90)
    
    for b in blocks:
        btype = "/clear" if b['is_clear'] else b['language']
        lines = f"L{b['start_line']}-L{b['end_line']}"
        print(f"  {b['index']:3d}  {b['md5']}  {b['byte_count']:6d}  {lines:>10}  {btype:<8}")
    
    # 전체 해시 (순서 의존적)
    all_content = '\n===SEPARATOR===\n'.join(b['content'] for b in blocks)
    total_md5 = hashlib.md5(all_content.encode('utf-8')).hexdigest()
    total_sha256 = hashlib.sha256(all_content.encode('utf-8')).hexdigest()
    
    print()
    print(f"  전체 통합 MD5:    {total_md5}")
    print(f"  전체 통합 SHA256: {total_sha256}")
    print()


# ─── 메인 ────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print("사용법:")
        print("  python3 prompt_extractor.py extract [원본.md] [출력디렉토리]")
        print("  python3 prompt_extractor.py verify  [원본.md] [프롬프트디렉토리]")
        print("  python3 prompt_extractor.py checksum [원본.md]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    # 원본 파일 경로
    if len(sys.argv) >= 3:
        source_file = sys.argv[2]
    else:
        source_file = find_original_file()
    
    if not os.path.exists(source_file):
        print(f"❌ 원본 파일을 찾을 수 없습니다: {source_file}")
        sys.exit(1)
    
    print(f"  원본 파일: {source_file}")
    
    # 추출
    blocks = extract_code_blocks(source_file)
    print(f"  추출된 코드 블록: {len(blocks)}개")
    
    if command == 'extract':
        output_dir = sys.argv[3] if len(sys.argv) >= 4 else './prompts'
        manifest_file = os.path.join(os.path.dirname(output_dir), 'manifest.json')
        
        # 저장
        save_prompt_files(blocks, output_dir)
        save_manifest(blocks, manifest_file)
        
        # 저장 후 즉시 검증
        matches, mismatches, errors = verify_files(blocks, output_dir)
        success = print_verification_report(blocks, matches, mismatches, errors)
        print_checksums(blocks)
        
        sys.exit(0 if success else 1)
    
    elif command == 'verify':
        prompts_dir = sys.argv[3] if len(sys.argv) >= 4 else './prompts'
        
        matches, mismatches, errors = verify_files(blocks, prompts_dir)
        success = print_verification_report(blocks, matches, mismatches, errors)
        
        sys.exit(0 if success else 1)
    
    elif command == 'checksum':
        print_checksums(blocks)
        sys.exit(0)
    
    else:
        print(f"❌ 알 수 없는 명령: {command}")
        print("   사용 가능: extract, verify, checksum")
        sys.exit(1)


if __name__ == '__main__':
    main()
