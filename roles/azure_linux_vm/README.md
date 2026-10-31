# Ansible Role: azure_linux_vm

Creates a public IP, network interface, and Linux virtual machine in an
existing Azure resource group and virtual network.

### Features

- Creates a static public IP address with the `Standard` SKU.
- Creates a network interface with a single IP configuration that is attached
  to the public IP.
- Creates a Linux virtual machine from a configurable image, size, and admin
  credentials.
- Tags the public IP, network interface, and VM with
  `environment`, `responsible`, and `"Ansible managed": "true"` for ownership
  and lifecycle tracking.
- Uses the virtual network and subnet created by the `azure_network` role.
- Validates required configuration, creates resources, and applies tags in
  independently selectable task groups.
- Is idempotent: existing resources are left in place and updated to match the
  configured values.

## Dependencies

### Required Roles

| Role | Required | Purpose |
| --- | --- | --- |
| `azure_resource_group` | Yes | Creates the resource group that holds the VM and its network resources. It must run before this role. |
| `azure_network` | Yes | Creates the virtual network and subnet used by the VM network interface. It must run before this role. |

### Optional Roles

| Role | Required | Purpose |
| --- | --- | --- |
| `update_inventory` | No | Runs after this role and writes the private IP of the created VM into the inventory as `ansible_host`. |

### External Requirements

- The `azure.azcollection` Ansible collection
- Azure credentials for the target subscription (see the repository
  `README.md`), passed through `.azure/credentials` or the `AZURE_*`
  environment variables
- A service principal with permission to create resource groups and resources
  inside them, for example the `Contributor` role on the subscription

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

The recommended configuration is the inventory. The shared values are taken
from `resource_group`, `location`, `env`, and `responsible`; VM-specific values
are taken from the role-specific variables. The network names are configured
for the `azure_network` role:

```yaml
resource_group: "rg-dev"
location: "westeurope"
env: "development"
responsible: "devops-team"

azure_linux_vm_name: "testvm1"
azure_linux_vm_size: "Standard_B1s"
azure_linux_vm_admin_username: "azureuser"
azure_linux_vm_admin_password: "<admin-password>"
azure_linux_vm_os_offer: "0001-com-ubuntu-server-jammy"
azure_linux_vm_os_sku: "22_04-lts-gen2"
azure_linux_vm_publisher: "Canonical"
azure_linux_vm_managed_disk_type: "Standard_LRS"

azure_linux_vm_public_ip_name: "pip-dev"

networkinterface_name: "mynic"
azure_linux_vm_networkinterface_ip_configurations_name: "ipconfig1"

azure_network_virtual_network_name: "vnet-dev"
azure_network_subnet_name: "subnet-dev"

azure_linux_vm_tags:
  "Ansible managed": "true"
  costCenter: "12345"
```

The `env` and `responsible` values here tag VM resources. Every VM resource that
supports Azure tags receives the tags from `azure_linux_vm_tags`; the role
automatically adds or overrides `environment` and `responsible` using the
shared values above. Add custom tags to the `azure_linux_vm_tags` mapping in
`roles/azure_linux_vm/defaults/main.yml` without changing the task files. The
`azure_network` role owns the virtual network and subnet, and gets its network
values from `azure_network_*` variables.

| Role variable | Default | Description |
| --- | --- | --- |
| `resource_group` | `""` | Shared input: name of the existing resource group that holds the resources. Required. |
| `location` | `""` | Shared input: Azure region for every created resource, for example `westeurope`. Required. |
| `env` | `""` | Shared input: value of the `environment` tag on the created resources. |
| `responsible` | `""` | Shared input: value of the `responsible` tag on the created resources. |
| `networkinterface_name` | `""` | Shared input: name of the created network interface. Required. |
| `azure_linux_vm_name` | `""` | Name of the Linux virtual machine. Required. |
| `azure_linux_vm_size` | `""` | Azure VM size, for example `Standard_B1s`. Required. |
| `azure_linux_vm_admin_username` | `""` | Admin user name for the VM. Required. |
| `azure_linux_vm_admin_password` | `""` | Admin password for the VM. Treat it as a secret and store it in a vault. Required. |
| `azure_linux_vm_os_offer` | `""` | Image offer, for example `0001-com-ubuntu-server-jammy`. Required. |
| `azure_linux_vm_os_sku` | `""` | Image SKU, for example `22_04-lts-gen2`. Required. |
| `azure_linux_vm_publisher` | `""` | Image publisher, for example `Canonical`. Required. |
| `azure_linux_vm_managed_disk_type` | `""` | Managed disk type of the OS disk, for example `Standard_LRS`. |
| `azure_linux_vm_public_ip_name` | `""` | Name of the created public IP address. Required. |
| `azure_linux_vm_networkinterface_ip_configurations_name` | `""` | Name of the IP configuration of the network interface. Required. |
| `azure_linux_vm_tags` | `{"Ansible managed": "true"}` | Additional Azure tags applied to the public IP, network interface, and VM. `environment` and `responsible` are always set from the shared inputs. |

Role variables can also be overridden directly in a playbook or on the command
line, for example:

```bash
ansible-playbook playbooks/create_azure_vm.yml \
  -e resource_group=rg-dev \
  -e location=westeurope \
  -e azure_linux_vm_name=testvm1
```

The role does not create the resource group, create a subscription, configure
Azure credentials, or assign roles on the resource group.

## Encrypted Data / Ansible Vault

The role requires `azure_linux_vm_admin_password`, a secret. Store it in an
Ansible Vault encrypted variable file rather than in plaintext in the
inventory. Azure credentials belong in `.azure/credentials` or in the `AZURE_*`
environment variables and must not be committed to the repository. You can
encrypt further environment-specific values in your inventory using the
standard Ansible Vault workflow if required.

## Tags

Available tags:

| Tag | Purpose |
|-------|---------|
| `validate_vm_configuration` | Validates required VM and network configuration without contacting Azure. |
| `create_vm` | Validates configuration and creates the public IP, network interface, and VM, without applying Azure tags. |
| `add_tags_to_vm` | Validates configuration and applies the configured Azure tags to the public IP, network interface, and VM. |

## Known Limitations

- The role creates a single VM, public IP, and network interface per run. To
  create several, include it multiple times with different variable values.
- The public IP address is always static and uses the `Standard` SKU.
- The virtual network and subnet are managed by the `azure_network` role.
- The role does not delete resources and does not manage credentials or role
  assignments.
- The role does not connect to the VM over SSH and does not configure the
  operating system inside it.

## Run Ansible

After configuring the inventory, run the repository playbook:

```bash
ansible-playbook playbooks/create_azure_vm.yml
```

Run the VM role phases independently with Ansible tags:

```bash
# Validate the VM configuration without contacting Azure
ansible-playbook playbooks/create_azure_vm.yml --tags validate_vm_configuration

# Validate and create the VM resources (the network must already exist)
ansible-playbook playbooks/create_azure_vm.yml --tags create_vm

# Validate and apply tags to the supported Azure resources
ansible-playbook playbooks/create_azure_vm.yml --tags add_tags_to_vm
```

Running the playbook without a tag creates the resource group, network, and VM
in order, then applies their tags. The subnet does not receive tags because the
Azure subnet module does not support them.

To validate the playbook without contacting Azure, run:

```bash
ansible-playbook -i inventory/hosts.ini --syntax-check playbooks/create_azure_vm.yml
```

## Deletion

Delete the whole resource group, and every resource it contains, with:

```bash
az group delete --name rg-dev
```

To delete only the VM before its network resources, use:

```bash
az vm delete --resource-group rg-dev --name testvm1 --yes
```

Add `--yes` to skip the confirmation prompt. Deleting a resource group removes
all resources inside it and cannot be undone, so confirm that the resource
group no longer contains anything that is still needed.
