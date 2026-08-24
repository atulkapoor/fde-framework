---
id: governed-tools
component: integration
approach: governed-tools
realizations:
  - {stack: plain-python, template: integration/governed-tools.plain.py.j2, provides: ToolBoundary}
  - {stack: mcp, template: integration/governed-tools.mcp.py.j2, provides: ToolBoundary}
evidence: {case_ids: [structured-extraction], confidence: medium, last_verified: 2026-08-21}
---
Implements governed-tools for integration, satisfying ToolBoundary.

The no-framework realization is not a stub. It is the answer whenever
nothing in the profile justifies carrying a library.
