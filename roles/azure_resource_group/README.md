# Ansible Role: azure_resource_group

Creates the Azure resource groups listed in the inventory.

### Features

- Creates every Azure resource group listed in `resource_groups`, in a chosen
  Azure region.
- Applies `environment` and `responsible` tags for ownership and lifecycle
  tracking.
- Is idempotent: an existing resource group is left in place and its tags are
  updated to match the configured values.
- Can be run before other Azure roles to prepare the resource groups they use.

## Dependencies

### Required Roles

| Role | Required | Purpose |
| --- | --- | --- |
| None | - | The role has no Ansible role dependencies. The target subscription must exist and the `Microsoft.Resources` provider must be available. |

### Optional Roles

| Role | Required | Purpose |
| --- | --- | --- |
| `azure_linux_vm` | No | Creates the VM and its network resources in the created resource group. Run it after this role. |

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

## Configuration

The recommended configuration is the inventory. The resource groups are taken
from `resource_groups` in `inventory/group_vars/all.yml`; the region comes from
the shared `location` variable. Each list entry is a mapping with the group
`name` and its required, non-empty `env` and `responsible` tags:

```yaml
location: "westeurope"
env: "development"
responsible: "devops-team"

resource_groups:
  - name: "rg-dev"
    env: "development"
    responsible: "devops-team"
  - name: "rg-test"
    env: "development"
    responsible: "devops-team"
```

Each entry creates one resource group, so adding an entry to the list is enough
to have the next run create it. Entries without a name or either tag, or with
empty values, fail validation before any resource group is created.

The `azure_linux_vm` role also uses `env` and `responsible` to tag VM
resources, but its values are configured separately from each resource group's
required tags.

A VM host still selects the resource group it belongs to with the singular
`resource_group` variable (see the `azure_linux_vm` role); that name has to be
the `name` of one of the entries in `resource_groups`.

| Role variable | Default | Description |
| --- | --- | --- |
| `resource_groups` | `[]` | List of resource groups to create. Each entry must be a mapping with non-empty `name`, `env`, and `responsible` string values. Required. |
| `location` | `""` | Azure region for every created resource group, for example `westeurope`. Required. |

Role variables can also be overridden directly in a playbook or on the command
line, for example:

```bash
ansible-playbook playbooks/create_resource_group.yml \
  -e '{"resource_groups": [{"name": "rg-dev", "env": "development", "responsible": "devops-team"}]}' \
  -e location=westeurope
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

- The role only creates the listed resource groups. Removing a name from
  `resource_groups` does not delete it in Azure, and the role never deletes a
  resource group or manages resources inside it.
- The role does not validate that the `resource_group` value of a VM host is
  one of the listed names.
- Every resource group entry must include non-empty `env` and `responsible`
  tags; shared tag fallbacks are not supported.
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

Use the dedicated deletion playbook to delete one resource group and every
resource it contains:

```bash
ansible-playbook playbooks/delete_azure_resource_group.yml
```

The playbook prompts for the resource group name and requires it to be entered
again exactly before deleting. It uses `force_delete_nonempty: true` with
`state: absent`; the Azure identity must have permission to delete the group
and its resources. Deletion is irreversible, so verify the name and contents
before confirming.

Validate the playbook without contacting Azure:

```bash
ansible-playbook --syntax-check playbooks/delete_azure_resource_group.yml
```
