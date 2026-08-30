---
id: environment_lifetime
type: enum
scope: environment
kind: requirement
weight: 0.5
asks: "Does this environment need to be destroyed cleanly, or does it live?"
ask_role: [admin, sponsor]
values: [ephemeral, permanent]
recognises:
  ephemeral: [per pull request, spin up and tear down, temporary environment, for the pilot]
  permanent: [in production, production environment, goes to production, it stays, it lives, long lived, permanent environment, environment is permanent, stays up]
---
Whether teardown is a requirement or dead weight.

This is the one thing a convergence tool genuinely cannot do. Something that
brings a machine towards a described state has no concept of un-doing, so where
an environment must vanish cleanly the state file earns its keep -- and where the
cluster lives for five years, it is bookkeeping for an event that never happens.
