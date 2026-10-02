# -*- coding: utf-8 -*-
"""A from-scratch demo of ONE workflow definition serving regions with
DIFFERENT approval rules - without forking the module per region.

The problem: a straightforward way to handle "region X needs an extra
compliance-review step before approval" is to copy the whole approval
module for region X and add the step. That works once. It stops working
the moment two regions need two different extra steps, or a shared step
needs a bugfix and someone forgets to apply it to all four forked copies.

The alternative demonstrated here: ONE ordered list of default stages,
plus small, explicit per-region overrides (insert a stage after another,
or skip one) stored as data. The workflow engine resolves the effective
stage list per region at runtime. The approval logic itself never
branches on region - only the stage list differs.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class InsertAfter:
    """Insert `stage` right after `after_stage` for a specific region."""
    after_stage: str
    stage: str


@dataclass
class SkipStage:
    """Omit `stage` entirely for a specific region."""
    stage: str


RegionOverride = InsertAfter | SkipStage


class UnknownStageError(Exception):
    pass


class WorkflowDefinition:
    def __init__(self, default_stages: list[str]):
        if len(set(default_stages)) != len(default_stages):
            raise ValueError("default_stages must not contain duplicates")
        self._default_stages = list(default_stages)
        self._region_overrides: dict[str, list[RegionOverride]] = {}

    def add_region_override(self, region: str, override: RegionOverride) -> None:
        target = override.after_stage if isinstance(override, InsertAfter) else override.stage
        if target not in self._default_stages:
            raise UnknownStageError(
                f"override references stage {target!r}, which isn't in the default stages"
            )
        self._region_overrides.setdefault(region, []).append(override)

    def stages_for_region(self, region: str) -> list[str]:
        """
        Resolve the effective, ordered stage list for a region: start from
        the shared defaults, then apply that region's overrides in the
        order they were added. Regions with no overrides get the plain
        defaults - this is the common case, and it costs nothing extra.
        """
        stages = list(self._default_stages)
        for override in self._region_overrides.get(region, []):
            if isinstance(override, SkipStage):
                stages = [s for s in stages if s != override.stage]
            elif isinstance(override, InsertAfter):
                idx = stages.index(override.after_stage)
                stages.insert(idx + 1, override.stage)
        return stages

    def next_stage(self, region: str, current_stage: str) -> str | None:
        """None means current_stage was the last stage for this region."""
        stages = self.stages_for_region(region)
        idx = stages.index(current_stage)
        return stages[idx + 1] if idx + 1 < len(stages) else None
