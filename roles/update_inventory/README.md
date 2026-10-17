# Ansible Role: update_inventory

Writes the private IP of an Azure VM into the `host_vars` file of its inventory
host as `ansible_host`.

### Features

- Looks up the private IP of the VM network interface through the Azure API.
- Writes the private IP as `ansible_host: <ip>` into
  `inventory/host_vars/<host>.yml`.
- Replaces an existing `ansible_host:` line instead of appending a duplicate,
  so repeated runs stay idempotent.
- Creates the `host_vars` directory and the host file when they do not exist
  yet.
- Targets the VM inventory host, so `resource_group` and
  `networkinterface_name` come from that host's own variables.

## Dependencies

### Required Roles

| Role | Required | Purpose |
| --- | --- | --- |
| `azure_linux_vm` | Yes | Creates the network interface and VM whose private IP this role reads. The network interface must exist before this role runs. |

### Optional Roles

| Role | Required | Purpose |
| --- | --- | --- |
| None | - | The role can run directly after any role that creates a network interface with a known name. |

### External Requirements

- The `azure.azcollection` Ansible collection
- Azure credentials for the target subscription (see the repository
  `README.md`), passed through `.azure/credentials` or the `AZURE_*`
  environment variables
- A service principal with read access to the network interface, for example the
  `Reader` role on the resource group

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

The recommended configuration is the inventory. The network interface is taken
from the `networkinterface_name` variable, the resource group from
`resource_group`:

```yaml
resource_group: "rg-dev"
networkinterface_name: "mynic"
```

The same values are already used by the `azure_linux_vm` role, so a shared inventory
entry works for both roles.

| Role variable | Default | Description |
| --- | --- | --- |
| `resource_group` | `""` | Shared input: name of the resource group that holds the network interface. Required. |
| `networkinterface_name` | `""` | Shared input: name of the network interface attached to the VM. Required. |
| `update_inventory_target_host` | `"{{ inventory_hostname }}"` | Inventory host whose `host_vars` file is updated. Defaults to the host the role runs for. |
| `update_inventory_host_vars_dir` | `"{{ inventory_dir }}/host_vars"` | Directory that holds the per-host variable files. |
| `update_inventory_host_vars_file` | `"{{ update_inventory_host_vars_dir }}/{{ update_inventory_target_host }}.yml"` | File that receives the `ansible_host:` line. |

Role variables can also be overridden directly in a playbook or on the command
line, for example:

```bash
ansible-playbook playbooks/update_inventory.yml \
  -l testvm1 \
  -e networkinterface_name=mynic
```

The role does not create the VM or the network interface, does not modify the
inventory file `inventory/hosts.ini`, and does not manage SSH credentials.

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
| `update_inventory` | Playbook-level tag on `playbooks/update_inventory.yml`. Runs the role. |

No role-specific task tags are defined inside the role.

## Known Limitations

- The role reads a single network interface and writes the private IP of its
  first IP configuration. A VM with several network interfaces or IP
  configurations is not fully covered.
- The role only writes the `ansible_host:` line. It leaves all other variables
  in the host file untouched.
- An empty or missing `networkinterface_name` makes the lookup return no result
  and the `Extract the private IP address` task fails.
- The role does not wait for the network interface or VM to finish
  provisioning; it expects them to exist when it runs.

## Run Ansible

After configuring the inventory, run the repository playbook:

```bash
ansible-playbook -i inventory/hosts.ini playbooks/update_inventory.yml
```

To validate the playbook without contacting Azure, run:

```bash
ansible-playbook -i inventory/hosts.ini --syntax-check playbooks/update_inventory.yml
```

## Deletion

The role creates no Azure resources, so there is nothing to delete with the
Azure CLI. To revert its change, remove the `ansible_host:` line from the host
file by hand or delete the generated host file, for example:

```bash
rm inventory/host_vars/<host>.yml
```
