# Role README template

Template for the `README.md` of a role. It is based on
`roles/azure_resource_group/README.md`. Copy this file to
`roles/<role_name>/README.md` and replace every placeholder (`<role_name>`,
`<short description>`, and so on). Never delete a section that does not apply;
write "None" or "-" instead, as shown in this template.

All content in this repository - roles, playbooks, tasks, READMEs, and
comments - is written in English.

---

# Ansible Role: <role_name>

<one line describing what the role creates or changes.>

### Features

- <Feature 1, e.g. creates a single Azure resource.>
- <Feature 2, e.g. applies tags for ownership and lifecycle tracking.>
- <Feature 3, e.g. idempotent: an existing resource is left in place.>
- <Feature 4, e.g. can run before other roles to prepare shared
  infrastructure.>

## Dependencies

### Required Roles

| Role | Required | Purpose |
| --- | --- | --- |
| None | - | The role has no Ansible role dependencies. <Otherwise name the role that must run first.> |

### Optional Roles

| Role | Required | Purpose |
| --- | --- | --- |
| None | - | <Or: name an optional role and its purpose.> |

### External Requirements

- The `azure.azcollection` Ansible collection
- Azure credentials for the target subscription (see the repository
  `README.md`), passed through `.azure/credentials` or the `AZURE_*`
  environment variables
- A service principal with sufficient permissions, for example `Contributor`
  on the subscription

Install the collection from the repository root with:

```bash
ansible-galaxy collection install -r requirements.yml --collections-path ./collections
```

## Supported Platforms

| Platform | Version |
| --- | --- |
| Ansible controller | Any platform supported by Ansible |

## Supported Clouds

| Cloud Platform | Supported |
| --- | --- |
| Azure | Yes |

## Usage

Include the role in a playbook that connects locally to Azure. The repository
entry point is `playbooks/<action>.yml`:

```yaml
---
- name: <play name>
  hosts: localhost
  connection: local
  tags: <action>
  roles:
    - role: <role_name>
```

<description: The role faces Azure and runs on the Ansible controller, so
`connection: local` is sufficient. Provisioning configuration comes from the
inventory, for example `inventory/group_vars/azure_vms.yml` or
`inventory/host_vars/<host>.yml`.>

## Configuration

The recommended configuration is the inventory. The values are taken from the
role variables:

```yaml
resource_group: "rg-dev"
location: "westeurope"
env: "development"
responsible: "devops-team"
```

The same values are already used by the `<related role>` role, so a shared
inventory entry works for both roles.

| Role variable | Default | Description |
| --- | --- | --- |
| `<var1>` | `""` | <Description, whether it is required.> |
| `<var2>` | `""` | <Description.> |
| `env` | `""` | Value of the `environment` tag on the resource. |
| `responsible` | `""` | Value of the `responsible` tag on the resource. |

Role variables can also be overridden directly in a playbook or on the command
line, for example:

```bash
ansible-playbook playbooks/<action>.yml \
  -e <var1>=<value> \
  -e location=westeurope
```

The role does not <list what the role deliberately skips, for example create
subscriptions, manage credentials, or assign roles>.

## Encrypted Data / Ansible Vault

The role does not require encrypted variables or Ansible Vault. Azure
credentials belong in `.azure/credentials` or in the `AZURE_*` environment
variables and must not be committed to the repository. You can encrypt
environment-specific values in your inventory using the standard Ansible Vault
workflow if required.

## Tags

Available tags:

| Tag | Purpose |
|-------|---------|
| `<action>` | Playbook-level tag on `playbooks/<action>.yml`. Runs the role. |

No role-specific task tags are defined inside the role.

## Known Limitations

- <Limitation 1: the role creates a single resource; several require multiple
  includes.>
- <Limitation 2: the role does not delete resources and does not manage
  resources inside them.>
- <Limitation 3: an attribute of an existing resource cannot be changed.>

## Run Ansible

After configuring the inventory, run the repository playbook:

```bash
ansible-playbook -i inventory/hosts.ini playbooks/<action>.yml
```

To validate the playbook without contacting Azure, run:

```bash
ansible-playbook -i inventory/hosts.ini --syntax-check playbooks/<action>.yml
```

## Deletion

Delete the created resources with the Azure CLI, for example:

```bash
az group delete --name <resource_group>
```

Add `--yes` to skip the confirmation prompt. Deleting removes all contained
resources and cannot be undone. Document the matching `az` commands for every
role in this section.
