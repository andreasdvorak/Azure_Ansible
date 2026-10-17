# Ansible Role: azure_linux_vm

Creates a virtual network, a subnet, a public IP, a network interface, and a
Linux virtual machine in an existing Azure resource group.

### Features

- Creates a virtual network with a configurable address prefix and a subnet
  inside it.
- Creates a static public IP address with the `Standard` SKU.
- Creates a network interface with a single IP configuration that is attached
  to the public IP.
- Creates a Linux virtual machine from a configurable image, size, and admin
  credentials.
- Tags the virtual network, public IP, network interface, and VM with
  `environment` and `responsible` for ownership and lifecycle tracking.
- Is idempotent: existing resources are left in place and updated to match the
  configured values.

## Dependencies

### Required Roles

| Role | Required | Purpose |
| --- | --- | --- |
| `azure_resource_group` | Yes | Creates the resource group that holds the VM and its network resources. It must run before this role. |

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

## Usage

Include the role in a playbook that targets the VM inventory group. The
repository entry point is `playbooks/create_vm.yml`, which runs the
`azure_resource_group` role first:

```yaml
---
- name: Provision Azure VM
  hosts: azure_vms
  connection: local
  tags: create_vm
  roles:
    - role: azure_resource_group
    - role: azure_linux_vm
```

The role faces Azure and runs on the Ansible controller, so
`connection: local` is sufficient. Provisioning configuration comes from the
inventory, for example `inventory/host_vars/testvm1.yml`.

## Configuration

The recommended configuration is the inventory. The shared values are taken
from `resource_group`, `location`, `env`, and `responsible`; the VM and network
resources are taken from the role-specific variables:

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

azure_linux_vm_virtual_network_name: "vnet-dev"
azure_linux_vm_virtual_network_address_prefixes: "10.0.1.0/24"
azure_linux_vm_subnet_name: "subnet-dev"
azure_linux_vm_public_ip_name: "pip-dev"

networkinterface_name: "mynic"
azure_linux_vm_networkinterface_ip_configurations_name: "ipconfig1"
```

The `env` and `responsible` values here tag VM resources. The
`azure_resource_group` role gets its required tags from each entry in
`resource_groups`; those values are configured separately.

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
| `azure_linux_vm_virtual_network_name` | `""` | Name of the created virtual network. Required. |
| `azure_linux_vm_virtual_network_address_prefixes` | `""` | Address prefix of the virtual network and the subnet, for example `10.0.1.0/24`. Required. |
| `azure_linux_vm_subnet_name` | `""` | Name of the created subnet. Required. |
| `azure_linux_vm_public_ip_name` | `""` | Name of the created public IP address. Required. |
| `azure_linux_vm_networkinterface_ip_configurations_name` | `""` | Name of the IP configuration of the network interface. Required. |

Role variables can also be overridden directly in a playbook or on the command
line, for example:

```bash
ansible-playbook playbooks/create_vm.yml \
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
| `create_vm` | Playbook-level tag on `playbooks/create_vm.yml`. Runs the `azure_resource_group` and `azure_linux_vm` roles. |

No role-specific task tags are defined inside the role.

## Known Limitations

- The role creates a single VM and one set of network resources per run. To
  create several, include it multiple times with different variable values.
- The subnet reuses the virtual network address prefix, so it always spans the
  whole virtual network address space.
- The public IP address is always static and uses the `Standard` SKU.
- The subnet cannot be tagged because `azure_rm_subnet` does not support tags.
- The role does not delete resources and does not manage credentials or role
  assignments.
- The role does not connect to the VM over SSH and does not configure the
  operating system inside it.

## Run Ansible

After configuring the inventory, run the repository playbook:

```bash
ansible-playbook -i inventory/hosts.ini playbooks/create_vm.yml
```

To validate the playbook without contacting Azure, run:

```bash
ansible-playbook -i inventory/hosts.ini --syntax-check playbooks/create_vm.yml
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
