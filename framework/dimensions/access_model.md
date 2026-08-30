---
id: access_model
type: enum
scope: non_functional
kind: requirement
weight: 1.0
asks: "Who may use this -- one operating team, distinct roles with different permissions, or anyone internal?"
values: [single_operator, role_based, open_internal]
recognises:
  single_operator: [one operating team, only the ops team, a single operator, one team uses it]
  role_based: [role-based access, rbac, different roles, per-role permissions, depends on the role, approvers and viewers]
  open_internal: [anyone in the company, any employee, org-wide access, everyone internally]
ask_role: ['admin', 'sponsor']
---
Who acts on the system, which is a different question from what the system
acts on. The posture section always said what stands in front of a mutative
step; this says who is allowed to stand there.

The answer moves the governance decision. Distinct roles mean the approval
gate must know which role approves -- an approval from someone who happens to
have a login is the accountability chain lost at the first link. One
operating team means the audit names people, not roles, and the ceremony of
role scoping is weight without work. Open internal access means per-user
approval is impossible by construction, so rate caps and the audit trail
carry what approval cannot.
