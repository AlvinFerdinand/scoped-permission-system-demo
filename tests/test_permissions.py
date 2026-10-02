# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from permissions import ALL_REGIONS, PermissionDeniedError, PermissionRegistry


def test_grant_in_one_region_does_not_leak_to_another_region():
    # The whole point of the two-dimensional scope: a supervisor approved
    # for one region must NOT inherit the same module in another region.
    reg = PermissionRegistry()
    reg.grant("supervisor", module="expenses", region="REGION-A", action="approve")

    assert reg.has_permission("supervisor", "expenses", "REGION-A", "approve")
    assert not reg.has_permission("supervisor", "expenses", "REGION-B", "approve")


def test_grant_in_one_module_does_not_leak_to_another_module():
    # ...and the mirror case: same region, different module, still denied.
    reg = PermissionRegistry()
    reg.grant("cashier", module="pos", region="REGION-A")

    assert reg.has_permission("cashier", "pos", "REGION-A")
    assert not reg.has_permission("cashier", "expenses", "REGION-A")


def test_wildcard_region_grants_every_region_for_that_module_only():
    # A headquarters auditor needs one module across all regions - but
    # still only that one module.
    reg = PermissionRegistry()
    reg.grant("auditor", module="expenses", region=ALL_REGIONS, action="read")

    assert reg.has_permission("auditor", "expenses", "REGION-A", "read")
    assert reg.has_permission("auditor", "expenses", "REGION-Z", "read")
    assert not reg.has_permission("auditor", "pos", "REGION-A", "read")


def test_action_is_part_of_the_scope_too():
    # Read access in a region must not imply approve access in it.
    reg = PermissionRegistry()
    reg.grant("clerk", module="expenses", region="REGION-A", action="read")

    assert reg.has_permission("clerk", "expenses", "REGION-A", "read")
    assert not reg.has_permission("clerk", "expenses", "REGION-A", "approve")


def test_require_permission_raises_with_all_four_scope_values():
    reg = PermissionRegistry()
    with pytest.raises(PermissionDeniedError) as exc_info:
        reg.require_permission("nobody", "expenses", "REGION-A", "approve")

    err = exc_info.value
    assert (err.user_id, err.module, err.region, err.action) == (
        "nobody", "expenses", "REGION-A", "approve"
    )


def test_revoke_removes_only_the_exact_scope():
    reg = PermissionRegistry()
    reg.grant("supervisor", "expenses", "REGION-A", "approve")
    reg.grant("supervisor", "expenses", "REGION-B", "approve")

    reg.revoke("supervisor", "expenses", "REGION-A", "approve")

    assert not reg.has_permission("supervisor", "expenses", "REGION-A", "approve")
    assert reg.has_permission("supervisor", "expenses", "REGION-B", "approve")


def test_regions_granted_for_module_lists_only_real_grants():
    reg = PermissionRegistry()
    reg.grant("supervisor", "expenses", "REGION-A", "approve")
    reg.grant("supervisor", "expenses", "REGION-C", "approve")
    reg.grant("supervisor", "pos", "REGION-D", "approve")

    assert reg.regions_granted_for_module("supervisor", "expenses", "approve") == {
        "REGION-A", "REGION-C"
    }


def test_regions_granted_for_module_collapses_to_wildcard():
    reg = PermissionRegistry()
    reg.grant("auditor", "expenses", ALL_REGIONS, "read")

    assert reg.regions_granted_for_module("auditor", "expenses", "read") == {ALL_REGIONS}


def test_user_with_no_grants_is_denied_everything():
    reg = PermissionRegistry()
    assert not reg.has_permission("stranger", "expenses", "REGION-A")
    assert reg.regions_granted_for_module("stranger", "expenses") == set()
