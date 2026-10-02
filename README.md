# scoped-permission-system-demo

Two ERP architecture patterns, written as clean-room demos — no real
company data, no real module or region names, nothing copied from any
employer/client codebase.

Both exist to solve the same underlying problem: **one system serving
many branches that don't all follow the same rules**, without forking the
code per branch.

---

## 1. Permissions scoped by module AND region, together

`permissions.py`

In a multi-branch organization, "can this user approve expense claims"
isn't one fact about the user:

- a regional supervisor approves expenses **for their region only**
- a headquarters auditor reads the expense module **across every region**
- a branch cashier gets point-of-sale access **in their own branch and nothing else**

A permission keyed on module alone (`can_approve_expenses: true`) breaks
the moment authority differs by region. A permission keyed on region
alone (`works_at: BRANCH-12`) breaks the moment two people at the same
branch need different modules. **Both dimensions have to be checked
together, independently.**

```python
reg = PermissionRegistry()
reg.grant("supervisor", module="expenses", region="REGION-A", action="approve")

reg.has_permission("supervisor", "expenses", "REGION-A", "approve")  # True
reg.has_permission("supervisor", "expenses", "REGION-B", "approve")  # False - no leak across regions
reg.has_permission("supervisor", "pos",      "REGION-A", "approve")  # False - no leak across modules
```

A wildcard region (`ALL_REGIONS`) covers the auditor case without
granting any extra module. Grants are **data** — adding a region, or a
one-off per-region exception, never touches module code.

## 2. One workflow definition, region-specific approval stages

`workflow.py`

The obvious way to handle "region X needs an extra compliance review
before approval" is to copy the approval module for region X. That works
exactly once — until two regions need two *different* extra steps, or a
shared step gets a bugfix that someone forgets to apply to all the forked
copies.

Instead: one ordered list of default stages, plus small explicit
per-region overrides stored as data. The approval logic itself never
branches on region — only the resolved stage list differs.

```python
wf = WorkflowDefinition(["submitted", "supervisor_review", "finance_review", "approved"])
wf.add_region_override("REGION-EXPORT", InsertAfter("supervisor_review", "compliance_review"))
wf.add_region_override("REGION-SMALL",  SkipStage("finance_review"))

wf.stages_for_region("REGION-EXPORT")
# ['submitted', 'supervisor_review', 'compliance_review', 'finance_review', 'approved']
wf.stages_for_region("REGION-SMALL")
# ['submitted', 'supervisor_review', 'approved']
wf.stages_for_region("REGION-PLAIN")
# unchanged defaults
```

An override referencing a stage that doesn't exist is rejected **at
configuration time**, not silently at runtime — a typo in a stage name
should never quietly produce a workflow that skips an approval step.

---

## Run the tests

```bash
pip install pytest
python -m pytest tests/ -v
```

18 tests, covering both directions of permission leakage (module→module
and region→region), wildcard grants, action-level scoping, revocation
precision, two regions with two different workflow overrides, override
stacking order, and config-time validation.

## Why this shape

This mirrors the access-control and workflow architecture I built for a
production ERP running across dozens of branches in several business
lines — originally in Laravel/PHP; rewritten here framework-agnostic in
Python so the pattern is readable on its own. The real system's code and
data aren't here and aren't mine to publish; what's demonstrated is the
design decision, which is the part worth discussing anyway.

## License

MIT.
