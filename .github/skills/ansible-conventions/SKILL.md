---
name: ansible-conventions
description: "Use when creating, editing, or reviewing anything in this Ansible project - roles, playbooks, inventory, or variables for Azure. Enforces the role layout, naming, playbook structure, Azure collection usage, and validation steps used in this repository."
---

# Ansible Conventions (Azure_Ansible)

Follow these conventions for every change in this repository. They match the
existing roles (`azure_linux_vm`, `azure_resource_group`, `update_inventory`) and playbooks.

## Language

Write repository content in English, including task names, variable names,
READMEs, playbook and role comments, and commit messages. This applies to
project files, not chat responses; respond to the user in the language they use.

## Repository layout

- Controller config: `ansible.cfg` sets `collections_path = ./collections`,
  `roles_path = ./roles`, and `inventory = ./inventory/hosts.ini`. Use these
  relative paths; do not invent new ones.
- Python interpreter: `.venv/bin/python` (virtualenv in the repo root).
- Azure collection: `collections/ansible_collections/azure/azcollection`,
  installed from `requirements.yml`.

## Creating a role

1. Read `references/role-template.md` for the expected file set and
   conventions before you start.
2. Use a snake_case role name (for example `azure_linux_vm`, `azure_resource_group`,
   `update_inventory`). `ansible-lint` enforces this via `role-name`
   (`^[a-z][a-z0-9_]*$`); never use camelCase such as `Linux_vm`.
3. Create `roles/<role_name>/tasks/main.yml` and
   `roles/<role_name>/defaults/main.yml`.
4. Every task starts with a clear, descriptive `name`.
5. Declare every input variable in `defaults/main.yml` with a safe empty
   default (`""`), and give every variable the role defines the role-name
   prefix required by `ansible-lint` (see "Role variable naming").
6. When `tasks/main.yml` dispatches to multiple task files with
   `ansible.builtin.import_tasks`, assign a descriptive, distinct `tags`
   value to each import so callers can select the relevant task group.
7. Add `roles/<role_name>/README.md` by copying
   `references/role-readme-template.md` and replacing the placeholders. Keep
   every section; write "None" or "-" when it does not apply instead of
   deleting it.
8. Keep the first documentation line free of `#` markers only where required;
   use standard Markdown headings.

## Azure modules

- Always use the fully qualified collection name
  (`azure.azcollection.azure_rm_<resource>`), never a short name.
- Prefer the native Ansible Azure modules for resources; the modules are
  idempotent, so do not add manual existence checks.
- Tag created resources with `environment: "{{ env }}"` and
  `responsible: "{{ responsible }}"` when the module supports `tags`.
- Never put credentials in the inventory. Use `.azure/credentials` or the
  `AZURE_CLIENT_ID`, `AZURE_SECRET`, `AZURE_TENANT`,
  `AZURE_SUBSCRIPTION_ID` environment variables.

## Playbooks

1. Read `references/playbook-template.md` before adding a playbook.
2. Place playbooks in `playbooks/<action>.yml` (for example
   `create_resource_group.yml`, `create_vm.yml`).
3. Give each play a descriptive `name`, `connection: local`, and a play-level
   `tags` value (for example `create_resource_group`).
4. Playbooks always run roles through the `roles:` keyword. Never use a
   `tasks:` block with `ansible.builtin.include_role` to call a role:

   ```yaml
   - name: Provision Azure resource group
     hosts: localhost
     connection: local
     tags: create_resource_group
     roles:
       - role: azure_resource_group
   ```

5. Use `hosts: localhost` for plays whose role talks to the Azure API, and the
   existing group (`azure`) only when a role must target VMs.
6. Do not inline configuration in playbooks unless the existing playbook does
   so; prefer inventory `group_vars`/`host_vars`.
7. Keep a `tasks:` block only for playbooks that run ad-hoc diagnostic tasks
   and no roles (for example `tests.yml`, `credential_test.yml`).
8. Reference the Python interpreter in Jinja as `{{ ansible_playbook_python }}`.
   The `ansible_python_interpreter` entry in `ansible.cfg` is only used for
   module interpreter discovery and is not defined as a template variable.

## Variables and inventory

- Shared variable names across roles: `resource_group`, `location`, `env`,
  `responsible`.
- Put shared values in `inventory/group_vars/` (`all.yml`,
  `azure.yml`) and per-host values in `inventory/host_vars/<host>.yml`.
- Role variables follow the prefix rule in "Role variable naming": every
  variable a role defines is prefixed with the role name, while shared
  inventory names (`resource_group`, `location`, `env`, `responsible`,
  `networkinterface_name`) keep their names.
- Never commit secrets. `inventory/host_vars/testvm1.yml` currently contains a
  plaintext password; treat any secret you touch as sensitive and move it to a
  vault rather than copying it elsewhere.

## Role variable naming

`ansible-lint` enforces `var-naming[no-role-prefix]`: "Variables names from
within roles should use `<role_name>_` as a prefix." Every variable a role
*defines* must therefore start with the role name:

- keys in `defaults/main.yml` and `vars/main.yml`,
- `set_fact:` keys,
- `register:` names,
- `vars:` passed to `include_role`/`import_role`.

For the role `update_inventory`, a task that looks up the network interface
uses `register: update_inventory_networkinterface_info`, not
`register: networkinterface_info`, and a fact is named
`update_inventory_private_ip`, not `vm_private_ip`. Variables whose name starts
with `ansible_` are owned by Ansible and are exempt from the rule.

Only shared input variables that the inventory and several roles use under the
same name stay unprefixed. `resource_group`, `location`, `env`, `responsible`,
and host values such as `networkinterface_name` keep their names and silence
the rule on the default line:

```yaml
resource_group: ""  # noqa: var-naming[no-role-prefix]
```

Never silence a role-internal variable this way; rename it with the role-name
prefix instead. Variables that appear only in a task's `vars:` block (not in
`include_role`/`import_role`) are task-scoped and need no prefix.

Fix a `var-naming[no-role-prefix]` finding before reporting a change as done;
do not leave it for the next run.

## Validation

Always run all of these before reporting a change as done:

1. Syntax-check every touched playbook:

   ```bash
   ansible-playbook playbooks/<playbook>.yml --syntax-check
   ```

2. YAML lint over the whole project:

   ```bash
   yamllint inventory playbooks roles
   ```

3. Ansible lint over the whole project:

   ```bash
   ansible-lint inventory playbooks roles
   ```

`scripts/validate.sh` runs all three steps (syntax-check for one or every
playbook, then `yamllint` and `ansible-lint` over `inventory`, `playbooks`,
and `roles`). Both linters are project requirements (`requirements.txt`).
Fix every finding; never report a change as complete while a linter still
fails.

`ansible-lint` prints `WARNING Directory expansion discovered N file(s)` as
soon as an argument is a directory (here `inventory`, `playbooks`, `roles`).
The warning is informational, does not affect the result, and `exclude_paths`
cannot remove it; the passed directories would still expand to files. Ignore
it, or run `ansible-lint -q inventory playbooks roles` to hide the warnings
(the exit code and the individual violations remain, but the rule summary does
not). Do not drop the directory arguments: `inventory/` is listed in
`.gitignore`, so a bare `ansible-lint` skips `group_vars` and `host_vars`.

The project `.yamllint` sets `comments`, `comments-indentation`, `braces` and
`octal-values` to the values `ansible-lint` requires. If those drift apart,
`ansible-lint` prints `WARNING Found incompatible custom yamllint configuration`
and silently disables its fix mode. Keep `.yamllint` in sync with the rules
listed in that warning.

## Deleting resources

Use the Azure CLI and document destructive commands in the role README under
"Deletion". For a resource group:

```bash
az group delete --name <resource_group>
```

## Reference files

- `references/role-template.md` - role file set and conventions.
- `references/role-readme-template.md` - full README template for a role,
  based on `roles/azure_resource_group/README.md`.
- `references/playbook-template.md` - playbook structure and examples.
- `scripts/validate.sh` - syntax-check playbooks.
