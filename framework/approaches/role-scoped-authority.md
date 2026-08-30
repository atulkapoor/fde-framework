---
id: role-scoped-authority
name: Role-scoped authority
complexity: 2
components: [governance]
applies_when: [access_model == role_based]
avoid_when: [access_model == single_operator, access_model == open_internal]
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-30}
---
Approval and audit that know which role is speaking.

The approval gate refuses an approval that does not carry an approver role,
and the audit records the role beside the person. Entitlements remain an
intersection -- what the delegating person may do, what the agent is scoped
to, what the tool requires -- with the role as a ceiling on the first term,
never an extension of it.

The roles themselves are client content: this approach fixes the contract
that a role must be named, and refuses to invent the names.
