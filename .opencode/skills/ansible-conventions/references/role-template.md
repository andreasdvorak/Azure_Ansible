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
- Each task has a descriptive `name`.
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
- name: Create resource group
  azure.azcollection.azure_rm_resourcegroup:
    name: "{{ resource_group }}"
    location: "{{ location }}"
    tags:
      environment: "{{ env }}"
      responsible: "{{ responsible }}"

- name: Look up something
  azure.azcollection.azure_rm_example_info:
    resource_group: "{{ resource_group }}"
  register: example_role_lookup_result

- name: Remember the result
  ansible.builtin.set_fact:
    example_role_result_id: "{{ example_role_lookup_result.id }}"
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
`roles/resource_group/README.md`). Copy it to `roles/<role_name>/README.md`,
replace the placeholders, and keep every section - write "None" or "-" when a
section does not apply instead of removing it.

Sections in order: `# Ansible Role: <role_name>` with a one-line description,
`### Features`, `## Dependencies` (Required Roles, Optional Roles, External
Requirements), `## Supported Platforms`, `## Supported Clouds`, `## Usage`,
`## Configuration`, `## Encrypted Data / Ansible Vault`, `## Tags`,
`## Known Limitations`, `## Run Ansible`, `## Deletion`.
