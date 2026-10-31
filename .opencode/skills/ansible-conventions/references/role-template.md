# Role template

Use this as the reference when creating or updating a role in this repository.

## File set

```text
roles/<role_name>/
├── tasks/
│   └── main.yml          # required
├── defaults/
│   └── main.yml          # required: declare every input variable here
└── README.md             # required: document the role
```

Optional additions, only when the role needs them: `vars/main.yml`,
`handlers/main.yml`, `templates/`, `files/`, `meta/main.yml`.

## Conventions

- Role and variable names in snake_case.
- `tasks/main.yml` starts with `---`.
- Every task has a descriptive `name`.
- The first task in `tasks/main.yml` validates all prerequisites with
  `ansible.builtin.assert` before any state change or Azure API call. Validate
  required inputs (including type and non-empty values), required mappings,
  and relevant relationships. Validation itself must not contact Azure.
- If tasks are selectable by action tags, tag the validation task with every
  action tag and a dedicated validation-only tag so selecting an action cannot
  bypass prerequisite validation.
- `tasks/main.yml` dispatches to action task files only after validation.
  Assign each `ansible.builtin.import_tasks` a descriptive, distinct action
  tag.
- Azure modules use the full name `azure.azcollection.azure_rm_<resource>`.
- Resource tags use `environment: "{{ env }}"` and
  `responsible: "{{ responsible }}"`.
- Input variables default to `""` in `defaults/main.yml`.
- Every variable the role defines is prefixed with the role name, in
  `defaults/main.yml`, `vars/main.yml`, `set_fact`, and `register`. Shared
  inventory inputs keep their names with `# noqa: var-naming[no-role-prefix]`.
  See the skill's "Role variable naming".

## Example `tasks/main.yml`

```yaml
---
- name: Validate required example role configuration
  ansible.builtin.assert:
    that:
      - resource_group is string
      - resource_group | trim | length > 0
      - location is string
      - location | trim | length > 0
    fail_msg: >-
      resource_group and location must be non-empty strings.
  tags:
    - validate_example_role
    - create_example_role
    - tag_example_role

- name: Create example resources
  ansible.builtin.import_tasks: create.yml
  tags:
    - create_example_role

- name: Add tags to example resources
  ansible.builtin.import_tasks: add_tags.yml
  tags:
    - tag_example_role
```

## Example `defaults/main.yml`

```yaml
---
# Shared inputs keep their inventory names.
resource_group: ""  # noqa: var-naming[no-role-prefix]
location: ""  # noqa: var-naming[no-role-prefix]
env: ""  # noqa: var-naming[no-role-prefix]
responsible: ""  # noqa: var-naming[no-role-prefix]

# Role-specific variables carry the role-name prefix.
example_role_result_id: ""
```

## README

Use the full template in `role-readme-template.md` (derived from
`roles/azure_resource_group/README.md`). Copy it to `roles/<role_name>/README.md`,
replace the placeholders, and keep every section - write "None" or "-" when a
section does not apply instead of removing it.

Sections in order: `# Ansible Role: <role_name>` with a one-line description,
`### Features`, `## Dependencies` (Required Roles, Optional Roles, External
Requirements), `## Supported Platforms`, `## Supported Clouds`, `## Usage`,
`## Configuration`, `## Encrypted Data / Ansible Vault`, `## Tags`,
`## Known Limitations`, `## Run Ansible`, `## Deletion`.
