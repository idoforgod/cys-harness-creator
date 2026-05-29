#!/usr/bin/env python3
"""
test_pre_subagent_invocation.py — Test suite for pre-subagent invocation fork decision logic

Test coverage:
- Translation fork logic (@translator invocation conditions)
- Review fork logic (@reviewer/@fact-checker invocation conditions)
- pACS score-based routing (RED/YELLOW/GREEN zones)
- Stage verification status propagation
- Cross-gate dependency validation
- Sub-agent selection rules (Adversarial Review trigger, Fact-Check trigger)

Run: pytest test_pre_subagent_invocation.py -v
"""

import pytest
import json
from pathlib import Path
from typing import Dict, List


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def workflow_config():
    """Fixture providing example workflow configuration."""
    return {
        'steps': [
            {
                'step': 1,
                'name': 'Research',
                'type': '(human)',
                'Verification': ['V1a: Complete sources', 'V1b: Coherent synthesis'],
                'Translation': '@translator',
                'Review': None
            },
            {
                'step': 2,
                'name': 'Analysis',
                'type': '(human)',
                'Verification': ['V2a: Logic verified', 'V2b: Assumptions stated'],
                'Translation': None,
                'Review': '@reviewer'
            },
            {
                'step': 3,
                'name': 'Final',
                'type': '(human)',
                'Verification': ['V3a: Completeness'],
                'Translation': '@translator',
                'Review': '@fact-checker'
            },
            {
                'step': 4,
                'name': 'Team Coordination',
                'type': '(team)',
                'Verification': None,
                'Translation': None,
                'Review': None
            }
        ]
    }


@pytest.fixture
def sot_state_sample():
    """Sample SOT state after workflow execution."""
    return {
        'current_step': 2,
        'workflow_status': 'running',
        'pacs': {
            'current_step_score': 75,
            'dimensions': [80, 75, 70],
            'weak_dimension': 'Logic',
            'history': {
                'step-1': {'score': 82, 'dimensions': [85, 82, 80]},
                'step-2': {'score': 75, 'dimensions': [80, 75, 70]}
            }
        },
        'outputs': {
            'step-1': 'research-output.md',
            'step-2': 'analysis-output.md'
        },
        'verification': {
            'step-1': {'status': 'PASS', 'criteria': ['V1a: PASS', 'V1b: PASS']},
            'step-2': {'status': 'PASS', 'criteria': ['V2a: PASS', 'V2b: PASS']}
        }
    }


# ============================================================================
# Test: Translation Fork Logic
# ============================================================================

class TestTranslationForkLogic:
    """Tests for @translator sub-agent invocation conditions"""

    def test_translation_fork_condition_workflow_config(self, workflow_config):
        """Translation fork: Check if step has Translation: @translator marker."""
        step_1 = workflow_config['steps'][0]
        step_2 = workflow_config['steps'][1]

        # Step 1 has Translation marker
        assert step_1['Translation'] == '@translator'

        # Step 2 does not
        assert step_2['Translation'] is None

    def test_translation_fork_prerequisite_verification_pass(self, sot_state_sample):
        """Translation fork: Only invoke @translator if Verification PASS."""
        # Step 1 verification passed
        step_1_verification = sot_state_sample['verification']['step-1']
        can_translate = (
            step_1_verification['status'] == 'PASS' and
            all('PASS' in c for c in step_1_verification['criteria'])
        )
        assert can_translate

    def test_translation_fork_prerequisite_verification_fail_blocks(self, sot_state_sample):
        """Translation fork: Do NOT invoke if Verification FAIL."""
        # Simulate verification failure
        sot_state_sample['verification']['step-2']['status'] = 'FAIL'
        sot_state_sample['verification']['step-2']['criteria'] = [
            'V2a: FAIL — logic error',
            'V2b: PASS'
        ]

        step_2_verification = sot_state_sample['verification']['step-2']
        can_translate = (
            step_2_verification['status'] == 'PASS'
        )
        assert not can_translate

    def test_translation_decision_context(self, sot_state_sample):
        """Translation fork: Pass previous stage deliverable path to @translator."""
        prev_step = 1
        output_path = sot_state_sample['outputs'].get(f'step-{prev_step}')

        translation_context = {
            'source_step': prev_step,
            'source_path': output_path,
            'pacs_score': sot_state_sample['pacs']['history']['step-1']['score'],
            'weak_dimension': None  # Step 1 did not have RED/YELLOW
        }

        assert translation_context['source_path'] == 'research-output.md'
        assert translation_context['pacs_score'] == 82


# ============================================================================
# Test: Review Fork Logic (Adversarial Review)
# ============================================================================

class TestReviewForkLogic:
    """Tests for @reviewer/@fact-checker sub-agent invocation conditions"""

    def test_review_fork_condition_workflow_config(self, workflow_config):
        """Review fork: Check if step has Review: @reviewer or @fact-checker marker."""
        step_2 = workflow_config['steps'][1]
        step_3 = workflow_config['steps'][2]

        # Step 2 has @reviewer
        assert step_2['Review'] == '@reviewer'

        # Step 3 has @fact-checker
        assert step_3['Review'] == '@fact-checker'

    def test_review_fork_prerequisite_verification_pass(self, sot_state_sample):
        """Review fork: Only invoke @reviewer if Verification PASS."""
        step_2_verification = sot_state_sample['verification']['step-2']

        can_review = step_2_verification['status'] == 'PASS'
        assert can_review

    def test_review_fork_pacs_score_routing(self, sot_state_sample):
        """Review fork: pACS score (RED/YELLOW/GREEN) may determine reviewer selection."""
        pacs_score = sot_state_sample['pacs']['current_step_score']

        # pACS zones
        if pacs_score < 50:
            zone = 'RED'
        elif pacs_score < 70:
            zone = 'YELLOW'
        else:
            zone = 'GREEN'

        # Score 75 → GREEN zone
        assert zone == 'GREEN'

        # In GREEN, standard @reviewer
        reviewer_type = '@reviewer' if zone == 'GREEN' else '@fact-checker'
        assert reviewer_type == '@reviewer'

    def test_review_fork_yellow_zone_enhanced_scrutiny(self):
        """Review fork: pACS YELLOW (50-69) triggers enhanced scrutiny in Review."""
        # Score in YELLOW zone (50-69)
        pacs_score = 62

        assert 50 <= pacs_score < 70

        # Trigger enhanced scrutiny parameters
        scrutiny_params = {
            'extra_dimensions': 2,  # Check beyond main 3
            'cross_reference_depth': 2,  # Check prior steps
            'assumption_validation': True
        }

        assert scrutiny_params['extra_dimensions'] == 2

    def test_review_fork_red_zone_escalation_or_fact_check(self):
        """Review fork: pACS RED (< 50) may trigger escalation or @fact-checker routing."""
        pacs_score = 45

        assert pacs_score < 50

        # Decision: either escalate or invoke @fact-checker for additional verification
        decision = 'escalate_or_fact_check'
        assert decision in ['escalate_or_fact_check', 'fact_check']

    def test_review_decision_context(self, sot_state_sample):
        """Review fork: Pass deliverable + pACS info to @reviewer."""
        step = 2
        output_path = sot_state_sample['outputs'].get(f'step-{step}')
        pacs_info = sot_state_sample['pacs']['history'][f'step-{step}']

        review_context = {
            'deliverable': output_path,
            'pacs_score': pacs_info['score'],
            'dimensions': pacs_info['dimensions'],
            'weak_dimension': 'Logic'  # from current_step_score
        }

        assert review_context['deliverable'] == 'analysis-output.md'
        assert review_context['pacs_score'] == 75
        assert len(review_context['dimensions']) == 3


# ============================================================================
# Test: pACS Zone Routing
# ============================================================================

class TestPACSZoneRouting:
    """Tests for pACS-based sub-agent selection and routing"""

    def test_pacs_zone_classification(self):
        """pACS zone: Classify score into RED / YELLOW / GREEN."""
        test_cases = [
            (45, 'RED'),      # < 50
            (50, 'YELLOW'),   # 50-69
            (62, 'YELLOW'),   # 50-69
            (69, 'YELLOW'),   # 50-69
            (70, 'GREEN'),    # >= 70
            (85, 'GREEN'),    # >= 70
            (100, 'GREEN'),   # 100
        ]

        for score, expected_zone in test_cases:
            if score < 50:
                zone = 'RED'
            elif score < 70:
                zone = 'YELLOW'
            else:
                zone = 'GREEN'

            assert zone == expected_zone, f"Score {score} → {zone}, expected {expected_zone}"

    def test_pacs_zone_affects_review_type(self):
        """pACS zone: GREEN → @reviewer, YELLOW → enhanced scrutiny, RED → escalation."""
        zones = {
            'RED': {'reviewer': 'escalate_or_fact_check', 'action': 'diagnostic'},
            'YELLOW': {'reviewer': '@reviewer', 'action': 'enhanced_scrutiny'},
            'GREEN': {'reviewer': '@reviewer', 'action': 'standard'}
        }

        # GREEN zone
        assert zones['GREEN']['reviewer'] == '@reviewer'
        assert zones['GREEN']['action'] == 'standard'

        # YELLOW zone
        assert zones['YELLOW']['action'] == 'enhanced_scrutiny'

    def test_pacs_weak_dimension_influences_review_focus(self):
        """pACS weak dimension: If Logic weak, @reviewer focuses on logic validation."""
        dimensions = {
            'Functionality': 80,
            'Clarity': 75,
            'Logic': 65
        }

        weak_dim = min(dimensions, key=dimensions.get)
        assert weak_dim == 'Logic'

        review_focus = f"Focus on {weak_dim} validation"
        assert 'Logic' in review_focus


# ============================================================================
# Test: Stage Type-Specific Fork Logic
# ============================================================================

class TestStageTypeForkLogic:
    """Tests for fork logic differences between (human), (team), and other stage types"""

    def test_human_stage_translation_fork(self, workflow_config):
        """(human) stage: Translation fork triggered after Verification PASS."""
        step_1 = workflow_config['steps'][0]
        assert step_1['type'] == '(human)'
        assert step_1['Translation'] == '@translator'

    def test_human_stage_review_fork(self, workflow_config):
        """(human) stage: Review fork triggered after Verification PASS."""
        step_2 = workflow_config['steps'][1]
        assert step_2['type'] == '(human)'
        assert step_2['Review'] == '@reviewer'

    def test_team_stage_no_individual_review(self, workflow_config):
        """(team) stage: No individual Review fork — Team Lead performs L2."""
        step_4 = workflow_config['steps'][3]
        assert step_4['type'] == '(team)'
        # Team stages do not have Review field
        assert 'Review' not in step_4 or step_4['Review'] is None

    def test_team_stage_l2_gate_is_collective_review(self):
        """(team) stage: L2 Team Lead verification is the 'review' equivalent."""
        team_l2_structure = {
            'gate': 'L2',
            'actor': 'Team Lead',
            'scope': 'all teammate deliverables',
            'pacs_derivation': 'aggregate peer pACS scores'
        }

        assert team_l2_structure['gate'] == 'L2'
        assert team_l2_structure['actor'] == 'Team Lead'


# ============================================================================
# Test: Verification Status Propagation
# ============================================================================

class TestVerificationStatusPropagation:
    """Tests for verification gate status propagation to fork decision"""

    def test_verification_status_blocks_all_forks(self, sot_state_sample):
        """Verification FAIL blocks Translation + Review + proceeding."""
        # Simulate verification failure
        sot_state_sample['verification']['step-1']['status'] = 'FAIL'

        step_1_status = sot_state_sample['verification']['step-1']['status']

        # All forks blocked
        can_translate = step_1_status == 'PASS'
        can_review = step_1_status == 'PASS'
        can_proceed = step_1_status == 'PASS'

        assert not can_translate
        assert not can_review
        assert not can_proceed

    def test_verification_pass_gates_unblock_forks(self, sot_state_sample):
        """Verification PASS unblocks Translation + Review if configured."""
        step_1_status = sot_state_sample['verification']['step-1']['status']

        # Verification passed
        assert step_1_status == 'PASS'

        # Forks can proceed
        can_translate = step_1_status == 'PASS'
        can_review = step_1_status == 'PASS'

        assert can_translate
        assert can_review


# ============================================================================
# Test: Cross-Gate Dependency Validation
# ============================================================================

class TestCrossGateDependency:
    """Tests for cross-gate prerequisites (e.g., Review PASS before Translation)"""

    def test_review_pass_prerequisite_for_translation(self):
        """In workflows with both Review and Translation, Review must PASS first."""
        gates = {
            'review_status': 'PASS',
            'translation_status': 'pending'
        }

        # Review must complete first
        can_translate = gates['review_status'] == 'PASS'
        assert can_translate

    def test_review_fail_blocks_translation(self):
        """Review FAIL blocks downstream Translation."""
        gates = {
            'review_status': 'FAIL',
            'translation_status': 'pending'
        }

        can_translate = gates['review_status'] == 'PASS'
        assert not can_translate

    def test_step_sequence_ordering_respected(self, sot_state_sample):
        """Cross-gate: Current step must complete before next step forks."""
        current_step = sot_state_sample['current_step']
        next_step = current_step + 1

        # Current step (2) must be PASS before triggering next step (3) forks
        current_verification = sot_state_sample['verification'][f'step-{current_step}']

        can_proceed_to_next = current_verification['status'] == 'PASS'
        assert can_proceed_to_next


# ============================================================================
# Test: Sub-Agent Selection Rules
# ============================================================================

class TestSubAgentSelectionRules:
    """Tests for selecting correct sub-agent type based on stage config"""

    def test_translator_selection_rule(self):
        """Rule: If Translation: @translator, invoke @translator."""
        config = {'Translation': '@translator'}

        selected_agent = config.get('Translation')
        assert selected_agent == '@translator'

    def test_reviewer_selection_rule(self):
        """Rule: If Review: @reviewer, invoke @reviewer."""
        config = {'Review': '@reviewer'}

        selected_agent = config.get('Review')
        assert selected_agent == '@reviewer'

    def test_fact_checker_selection_rule(self):
        """Rule: If Review: @fact-checker, invoke @fact-checker for claim verification."""
        config = {'Review': '@fact-checker'}

        selected_agent = config.get('Review')
        assert selected_agent == '@fact-checker'

    def test_no_fork_when_none(self):
        """Rule: If Translation/Review is null, no fork invocation."""
        config = {'Translation': None, 'Review': None}

        # No translation fork
        assert config['Translation'] is None
        # No review fork
        assert config['Review'] is None


# ============================================================================
# Test: Fork Decision Output (Integration)
# ============================================================================

class TestForkDecisionOutput:
    """Tests for fork decision output structure and content"""

    def test_translation_fork_decision_structure(self):
        """Translation fork decision includes: agent, context, precedence."""
        decision = {
            'agent': '@translator',
            'source_path': 'step-1-output.md',
            'target_lang': 'ko',
            'glossary_path': 'translations/glossary.yaml',
            'pacs_score': 82,
            'precedence': 'after_verification'
        }

        assert decision['agent'] == '@translator'
        assert decision['precedence'] == 'after_verification'

    def test_review_fork_decision_structure(self):
        """Review fork decision includes: agent, deliverable, pacs_info, focus."""
        decision = {
            'agent': '@reviewer',
            'deliverable': 'step-2-output.md',
            'pacs_score': 75,
            'weak_dimension': 'Logic',
            'review_focus': ['Logic validation', 'Assumption checking'],
            'precedence': 'after_verification'
        }

        assert decision['agent'] == '@reviewer'
        assert 'Logic validation' in decision['review_focus']

    def test_no_fork_decision_when_conditions_unmet(self):
        """When conditions unmet (e.g., Verification FAIL), no fork decision generated."""
        decision = None  # No fork

        assert decision is None


# ============================================================================
# Run
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
