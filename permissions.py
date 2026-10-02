# -*- coding: utf-8 -*-
"""A from-scratch demo of a permission system scoped by TWO independent
dimensions at once: module AND region. Clean-room code showing the
pattern - no real company data, no real module/region names.

The problem this solves: in a multi-branch organization, "can this user
approve expense claims" is not one yes/no fact about the user. A regional
supervisor should approve expense claims for THEIR region only; a
headquarters auditor might need read access to the expense module across
EVERY region; a branch cashier needs point-of-sale access only in their
own branch and nothing else.

A permission system keyed on module alone ("can approve: expenses") is
wrong the moment a user's authority differs by region. A permission
system keyed on region alone ("works at: Branch 12") is wrong the moment
two users at the same branch need different module access. You need
both dimensions checked together, independently - that's what this
demonstrates.

One workflow/module definition can then serve branches with different
access rules, instead of forking the module's code per branch - which is
the actual payoff: the module logic stays single, the access grants are
data, not code.
"""
from __future__ import annotations

from dataclasses import dataclass, field

ALL_REGIONS = "*"  # a grant using this wildcard applies to every region


@dataclass(frozen=True)
class Grant:
    module: str
    region: str  # a specific region code, or ALL_REGIONS
    action: str = "access"  # e.g. "access", "approve", "export" - kept generic here


class PermissionDeniedError(Exception):
    def __init__(self, user_id: str, module: str, region: str, action: str):
        super().__init__(
            f"user {user_id!r} may not {action!r} module {module!r} in region {region!r}"
        )
        self.user_id = user_id
        self.module = module
        self.region = region
        self.action = action


class PermissionRegistry:
    """
    Grants are data: a flat list of (module, region, action) tuples per
    user, not a hierarchy and not hardcoded per module. A new region, or a
    new per-region exception, is a data change - no code touched, no
    module forked.
    """

    def __init__(self):
        self._grants: dict[str, set[Grant]] = {}

    def grant(self, user_id: str, module: str, region: str, action: str = "access") -> None:
        self._grants.setdefault(user_id, set()).add(Grant(module, region, action))

    def revoke(self, user_id: str, module: str, region: str, action: str = "access") -> None:
        self._grants.get(user_id, set()).discard(Grant(module, region, action))

    def has_permission(self, user_id: str, module: str, region: str, action: str = "access") -> bool:
        grants = self._grants.get(user_id, set())
        return (
            Grant(module, region, action) in grants
            or Grant(module, ALL_REGIONS, action) in grants
        )

    def require_permission(self, user_id: str, module: str, region: str, action: str = "access") -> None:
        if not self.has_permission(user_id, module, region, action):
            raise PermissionDeniedError(user_id, module, region, action)

    def regions_granted_for_module(self, user_id: str, module: str, action: str = "access") -> set[str]:
        """
        Every region a user can act in for a module - used to render "pick
        a region" dropdowns scoped to what the user can actually touch,
        not the full region list filtered client-side (a real source of
        bugs: filtering what's SHOWN instead of what's actually ALLOWED
        means the server must still check independently on write).
        """
        grants = self._grants.get(user_id, set())
        if Grant(module, ALL_REGIONS, action) in grants:
            return {ALL_REGIONS}
        return {g.region for g in grants if g.module == module and g.action == action}
