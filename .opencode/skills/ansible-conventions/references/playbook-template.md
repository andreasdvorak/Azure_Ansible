# Playbook template

Use this as the reference when creating or updating a playbook in this
repository.

## Location and naming

- Place playbooks in `playbooks/<action>.yml`, for example
  `create_resource_group.yml`, `create_vm.yml`, `update_inventory.yml`.

## Conventions

- Every play has a descriptive `name`.
- Playbooks always call roles through the `roles:` keyword. Do not use a
  `tasks:` block with `ansible.builtin.include_role` to run a role.
- Plays whose role talks to the Azure API use `hosts: localhost` and
  `connection: local`.
- Add a play-level `tags` value, matching the playbook action. The tag applies
  to every role in the play.
- Keep configuration in inventory; do not inline it unless the existing
  playbook already does.

## Example playbook

```yaml
---
- name: Provision Azure resource group
  hosts: localhost
  connection: local
  tags: create_resource_group
  roles:
    - role: resource_group
```

## Multiple roles

List roles in the order they must run:

```yaml
---
- name: Provision Azure resource group and VM
  hosts: azure_vms
  connection: local
  tags: create_vm
  roles:
    - role: resource_group
    - role: linux_vm
```

Role-specific variables or tags can be set next to the role:

```yaml
  roles:
    - role: resource_group
      vars:
        resource_group: "rg-dev"
      tags: create_resource_group
```

## Running against VMs

When a role must run against VM hosts, target the existing group:

```yaml
---
- name: Provision Azure VM
  hosts: azure_vms
  connection: local
  tags: create_vm
  roles:
    - role: linux_vm
```

`connection: local` is still used because the Azure modules call the Azure API
from the controller rather than connecting over SSH.

## Validation

Run the full check before finishing a playbook change:

```bash
ansible-playbook playbooks/<playbook>.yml --syntax-check
yamllint inventory playbooks roles
ansible-lint inventory playbooks roles
```

Or run everything at once:

```bash
scripts/validate.sh <playbook>.yml
```
