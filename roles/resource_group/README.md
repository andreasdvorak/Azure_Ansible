# Ansible Role: resource_group

Creates an Azure resource group.

### Features

- Creates a single Azure resource group in a chosen Azure region.
- Applies `environment` and `responsible` tags for ownership and lifecycle
  tracking.
- Is idempotent: an existing resource group is left in place and its tags are
  updated to match the configured values.
- Can be run before other Azure roles to prepare the resource group they use.

## Dependencies

### Required Roles

| Role | Required | Purpose |
| --- | --- | --- |
| None | - | The role has no Ansible role dependencies. The target subscription must exist and the `Microsoft.Resources` provider must be available. |

### Optional Roles

| Role | Required | Purpose |
| --- | --- | --- |
| None | - | The role can be used as the first role in a play that creates further Azure resources in the same resource group. |

### External Requirements

- The `azure.azcollection` Ansible collection
- Azure credentials for the target subscription (see the repository
  `README.md`) passed through `.azure/credentials` or the `AZURE_*`
  environment variables
- A service principal with permission to create resource groups, for example
  the `Contributor` role on the subscription

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
entry point is `playbooks/create_resource_group.yml`:

```yaml
- name: Provision Azure resource group
  hosts: localhost
  connection: local
  tags: create_resource_group
  tasks:
    - name: Include resource_group role to create resource group
      ansible.builtin.include_role:
        name: resource_group
```

The role faces Azure and runs on the Ansible controller, so `connection: local`
is sufficient. Provisioning configuration comes from the inventory, for
example `inventory/host_vars/testvm1.yml` or `inventory/group_vars/azure_vms.yml`.

## Configuration

The recommended configuration is the inventory. The resource group name,
location, and tags are taken from the `resource_group`, `location`, `env`, and
`responsible` variables:

```yaml
resource_group: "rg-dev"
location: "westeurope"
env: "development"
responsible: "devops-team"
```

The same values are already used by the `linux_vm` role, so a shared inventory
entry works for both roles.

| Role variable | Default | Description |
| --- | --- | --- |
| `resource_group` | `""` | Name of the resource group to create. Required. |
| `location` | `""` | Azure region for the resource group, for example `westeurope`. Required. |
| `env` | `""` | Value of the `environment` tag on the resource group. |
| `responsible` | `""` | Value of the `responsible` tag on the resource group. |

Role variables can also be overridden directly in a playbook or on the command
line, for example:

```bash
ansible-playbook playbooks/create_resource_group.yml \
  -e resource_group=rg-dev \
  -e location=westeurope \
  -e env=development \
  -e responsible=devops-team
```

The role does not create a subscription, configure Azure credentials, or assign
roles on the resource group.

## Encrypted Data / Ansible Vault

The role does not require encrypted variables or Ansible Vault. Azure
credentials should be stored in `.azure/credentials` or supplied through the
`AZURE_*` environment variables rather than committed to the inventory. You can
encrypt environment-specific values in your inventory using the standard
Ansible Vault workflow if required.

## Tags

Available tags:

| Tag | Purpose |
|-------|---------|
| `create_resource_group` | Playbook-level tag on `playbooks/create_resource_group.yml`. Runs the role. |

No role-specific task tags are defined inside the role.

## Known Limitations

- The role creates a single resource group. To create several, include it
  multiple times with different variable values, or loop over it in a playbook.
- The role does not delete resource groups and does not manage resources inside
  them.
- The role does not create or configure the Azure subscription, credentials, or
  role assignments.
- Changing `location` for an existing resource group has no effect: an Azure
  resource group's region cannot be changed.

## Run Ansible

After configuring the inventory, run the repository playbook:

```bash
ansible-playbook playbooks/create_resource_group.yml
```

To validate the playbook without contacting Azure, run:

```bash
ansible-playbook --syntax-check playbooks/create_resource_group.yml
```

## Deletion

Delete the resource group, and every resource it contains, with:

```bash
az group delete --name rg-dev
```

Add `--yes` to skip the confirmation prompt. Deleting a resource group removes
all resources inside it and cannot be undone, so confirm that the resource
group no longer contains anything that is still needed.
