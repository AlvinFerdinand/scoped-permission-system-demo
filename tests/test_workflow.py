# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from workflow import InsertAfter, SkipStage, UnknownStageError, WorkflowDefinition

DEFAULT_STAGES = ["submitted", "supervisor_review", "finance_review", "approved"]


def test_region_without_overrides_gets_the_plain_defaults():
    wf = WorkflowDefinition(DEFAULT_STAGES)
    assert wf.stages_for_region("REGION-A") == DEFAULT_STAGES


def test_region_can_require_an_extra_stage_without_affecting_other_regions():
    # The payoff: ONE definition, one region needs an extra compliance
    # step, and no other region's flow changes at all.
    wf = WorkflowDefinition(DEFAULT_STAGES)
    wf.add_region_override(
        "REGION-EXPORT",
        InsertAfter(after_stage="supervisor_review", stage="compliance_review"),
    )

    assert wf.stages_for_region("REGION-EXPORT") == [
        "submitted", "supervisor_review", "compliance_review", "finance_review", "approved",
    ]
    assert wf.stages_for_region("REGION-A") == DEFAULT_STAGES


def test_region_can_skip_a_stage():
    wf = WorkflowDefinition(DEFAULT_STAGES)
    wf.add_region_override("REGION-SMALL", SkipStage(stage="finance_review"))

    assert wf.stages_for_region("REGION-SMALL") == [
        "submitted", "supervisor_review", "approved",
    ]


def test_two_regions_can_have_two_different_extra_stages():
    # The case that breaks the "just fork the module per region" approach.
    wf = WorkflowDefinition(DEFAULT_STAGES)
    wf.add_region_override(
        "REGION-EXPORT", InsertAfter("supervisor_review", "compliance_review")
    )
    wf.add_region_override(
        "REGION-GOV", InsertAfter("finance_review", "procurement_audit")
    )

    assert wf.stages_for_region("REGION-EXPORT") == [
        "submitted", "supervisor_review", "compliance_review", "finance_review", "approved",
    ]
    assert wf.stages_for_region("REGION-GOV") == [
        "submitted", "supervisor_review", "finance_review", "procurement_audit", "approved",
    ]
    assert wf.stages_for_region("REGION-PLAIN") == DEFAULT_STAGES


def test_overrides_stack_in_the_order_they_were_added():
    wf = WorkflowDefinition(DEFAULT_STAGES)
    wf.add_region_override("REGION-X", InsertAfter("supervisor_review", "compliance_review"))
    wf.add_region_override("REGION-X", SkipStage("finance_review"))

    assert wf.stages_for_region("REGION-X") == [
        "submitted", "supervisor_review", "compliance_review", "approved",
    ]


def test_next_stage_follows_the_regions_own_resolved_list():
    wf = WorkflowDefinition(DEFAULT_STAGES)
    wf.add_region_override("REGION-EXPORT", InsertAfter("supervisor_review", "compliance_review"))

    # Same current stage, two regions, two different next steps.
    assert wf.next_stage("REGION-EXPORT", "supervisor_review") == "compliance_review"
    assert wf.next_stage("REGION-A", "supervisor_review") == "finance_review"


def test_next_stage_returns_none_at_the_end():
    wf = WorkflowDefinition(DEFAULT_STAGES)
    assert wf.next_stage("REGION-A", "approved") is None


def test_override_referencing_an_unknown_stage_is_rejected_immediately():
    # Fail at configuration time, not silently at runtime in production -
    # a typo'd stage name should never quietly produce a workflow that
    # skips an approval step.
    wf = WorkflowDefinition(DEFAULT_STAGES)
    with pytest.raises(UnknownStageError):
        wf.add_region_override("REGION-A", InsertAfter("suprvisor_review", "extra"))
    with pytest.raises(UnknownStageError):
        wf.add_region_override("REGION-A", SkipStage("finanace_review"))


def test_duplicate_default_stages_are_rejected():
    with pytest.raises(ValueError):
        WorkflowDefinition(["submitted", "approved", "submitted"])
