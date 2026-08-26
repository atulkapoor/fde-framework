---
id: operates_after_handover
type: enum
kind: requirement
weight: 1.0
asks: "Who operates this after we leave?"
ask_role: [admin, sponsor, skeptic]
values: [platform_team, app_team, vendor, nobody_yet]
recognises:
  platform_team: [our platform team, our infrastructure team, our sre team]
  app_team: [the application team, the product team will run it]
  vendor: [managed for us, a vendor will run it]
  nobody_yet: [we have not decided who, no one owns it yet, tbd who runs it]
---
The question that decides whether a design survives contact with the year after
the engagement.

A self-hosted model with nobody named to operate it is not a solution, it is a
liability handed over with a bow on it. This is the dimension that should stop
an FDE recommending something impressive that quietly requires a team the client
does not have -- and it is usually discovered late, when it is expensive.

Ask the skeptic as well as the sponsor. They tend to know which of the last
three projects failed here.
