---
id: existing_iac_tool
type: enum
kind: environment
asks: "What does the team already use to manage infrastructure?"
ask_role: [admin]
values: [terraform, ansible, pulumi, cloudformation, none]
recognises:
  ansible: [we use ansible, ansible playbooks, our playbooks]
  terraform: [we use terraform, terraform modules, our tf]
  pulumi: [we use pulumi]
  cloudformation: [cloudformation, cdk, sam templates]
  none: [nothing yet, click ops, we do it by hand]
---
What the team already operates, which outranks what anybody would prefer.

They maintain this after the engagement ends. Handing a shop that lives in
Ansible a Terraform codebase is a disservice regardless of how clean the HCL is,
because the thing they cannot maintain is the thing that rots first.

Ansible provisions perfectly well through cloud modules. The argument that it
is only a configuration tool is a taxonomy argument, and taxonomy is not who
gets paged.
