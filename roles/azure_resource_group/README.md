# Ansible Role: azure_resource_group

Creates the Azure resource groups listed in the inventory.

### Features

- Creates every Azure resource group listed in `resource_groups`, in a chosen
  Azure region.
- Creates resource groups and applies tags in separate, independently
  selectable task groups.
- Applies `environment` and `responsible` tags for ownership and lifecycle
  tracking, the `"Ansible managed": "true"` marker, plus optional custom Azure
  tags for each resource group.
- Is idempotent: an existing resource group is left in place and its tags are
  updated to match the configured values.
- Can be run before other Azure roles to prepare the resource groups they use.
- Supports Ansible tags to run resource group validation or creation selectively.

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
`name` and its required, non-empty `env` and `responsible` values. Add an
optional `tags` mapping for additional Azure tags:

```yaml
location: "westeurope"

resource_groups:
  - name: "rg-dev"
    env: "development"
    responsible: "devops-team"
    tags:
      costCenter: "12345"
      owner: "platform-team"
  - name: "rg-test"
    env: "development"
    responsible: "devops-team"
```

Each entry creates one resource group, so adding an entry to the list is enough
to have the next run create it. Entries without a name or either required value,
or with empty values, fail validation before any resource group is created.
Optional `tags` must be a mapping. The role always sets `environment` from
`env`, `responsible` from `responsible`, and `"Ansible managed": "true"`; these
role-managed tags take precedence over matching keys in the optional mapping.
Add default tags shared by all resource groups to the
`azure_resource_group_tags` mapping in
`roles/azure_resource_group/defaults/main.yml`; no task changes are needed.

The `azure_linux_vm` role also uses `env` and `responsible` to tag VM
resources, but its values are configured separately from each resource group's
required tags.

A VM host still selects the resource group it belongs to with the singular
`resource_group` variable (see the `azure_linux_vm` role); that name has to be
the `name` of one of the entries in `resource_groups`.

| Role variable | Default | Description |
| --- | --- | --- |
| `resource_groups` | `[]` | List of resource groups to create. Each entry must include non-empty `name`, `env`, and `responsible` string values, and may include a `tags` mapping of additional Azure tags. |
| `azure_resource_group_tags` | `{"Ansible managed": "true"}` | Default Azure tags applied to every resource group. Add shared tags here; per-group `tags` may add extra keys, while defaults take precedence for duplicate keys. |
| `location` | `""` | Azure region for every created resource group, for example `westeurope`. Required. |

Role variables can also be overridden directly in a playbook or on the command
line, for example:

```bash
ansible-playbook playbooks/create_azure_resource_group.yml \
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

Available Ansible tags:

| Tag | Purpose |
|-------|---------|
| `create_resource_group` | Validates the configuration and creates the configured resource groups without setting tags. |
| `add_tags_to_resource_group` | Validates the configuration and applies the configured Azure tags to the resource groups. |
| `validate_resource_group` | Runs only the resource group configuration validation task. Use with `--tags validate_resource_group`. |

## Known Limitations

- The role only creates the listed resource groups. Removing a name from
  `resource_groups` does not delete it in Azure, and the role never deletes a
  resource group or manages resources inside it.
- The role does not validate that the `resource_group` value of a VM host is
  one of the listed names.
- Every resource group entry must include non-empty `env` and `responsible`
  values; shared tag fallbacks are not supported.
- Custom Azure tags must be provided as a mapping; the role-managed
  `environment` and `responsible` values take precedence.
- The role does not create or configure the Azure subscription, credentials, or
  role assignments.
- Changing `location` for an existing resource group has no effect: an Azure
  resource group's region cannot be changed.

## Run Ansible

After configuring the inventory, run the repository playbook:

```bash
ansible-playbook playbooks/create_azure_resource_group.yml
```

Create the resource groups or manage their tags independently with Ansible tags:

```bash
# Validate resource group configuration without contacting Azure
ansible-playbook playbooks/create_azure_resource_group.yml --tags validate_resource_group

# Validate and create resource groups without setting tags
ansible-playbook playbooks/create_azure_resource_group.yml --tags create_resource_group

# Validate and apply resource group tags
ansible-playbook playbooks/create_azure_resource_group.yml --tags add_tags_to_resource_group
```

Running the playbook without a tag creates the resource groups and then applies
their tags. Running only `add_tags_to_resource_group` also ensures the
resource groups exist, because the Azure module uses `state: present`.

To validate the playbook without contacting Azure, run:

```bash
ansible-playbook --syntax-check playbooks/create_azure_resource_group.yml
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
