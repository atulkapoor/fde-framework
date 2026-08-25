---
id: container_competence
type: boolean
kind: environment
asks: "Does the team that will operate this already run containers?"
ask_role: [admin, skeptic]
recognises:
  "true": [we run kubernetes, we use docker, containerised already, our containers]
---
Whether containers are something this team already does.

The container runtime is cheap -- namespaces and cgroups, near-zero overhead
against a bare process. What costs is the platform around it, and the largest
part of that cost is human: a team that does not run containers is being handed
a permanent competency requirement it did not ask for.

Ask the skeptic as well as the admin. "We are moving to containers" and "we run
containers" are different answers, and only one of them is true today.
