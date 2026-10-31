# Ansible Role: azure_network

Creates and tags an Azure virtual network and creates a subnet within it.

### Features

- Creates an Azure virtual network and subnet using configurable address
  prefixes.
- Applies `environment`, `responsible`, and configurable default tags to the
  virtual network.
- Validates configuration before any Azure API calls.
- Supports separate Ansible tags for network creation and tag management.

## Dependencies

### Required Roles

| Role | Required | Purpose |
| --- | --- | --- |
| `azure_resource_group` | Yes | Creates the resource group that contains the network. Run it before this role. |

### Optional Roles

| Role | Required | Purpose |
| --- | --- | --- |
| `azure_linux_vm` | No | Creates a VM and network interface that use the virtual network and subnet. Run it after this role. |

### External Requirements

- The `azure.azcollection` Ansible collection
- Azure credentials for the target subscription (see the repository
  `README.md`) passed through `.azure/credentials` or the `AZURE_*`
  environment variables
- A service principal with permission to create virtual networks and subnets
  in the target resource group

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

Configure the shared resource group and location values, plus network-specific
settings, in the inventory:

```yaml
resource_group: "rg-dev"
location: "westeurope"
env: "development"
responsible: "devops-team"

azure_network_virtual_network_name: "vnet-dev"
azure_network_virtual_network_address_prefixes: "10.0.0.0/16"
azure_network_subnet_name: "subnet-dev"
azure_network_subnet_address_prefix: "10.0.1.0/24"

azure_network_tags:
  "Ansible managed": "true"
  costCenter: "12345"
```

`azure_network_tags` is a mapping of default tags for the virtual network.
The role always sets `environment` from `env` and `responsible` from
`responsible`, overriding those keys if they appear in `azure_network_tags`.
The Azure subnet module does not support resource tags.

| Role variable | Default | Description |
| --- | --- | --- |
| `resource_group` | `""` | Shared input: name of the existing resource group. Required. |
| `location` | `""` | Shared input: Azure region, for example `westeurope`. Required. |
| `env` | `""` | Shared input: value of the virtual network's `environment` tag. Required. |
| `responsible` | `""` | Shared input: value of the virtual network's `responsible` tag. Required. |
| `azure_network_virtual_network_name` | `""` | Name of the virtual network. Required. |
| `azure_network_virtual_network_address_prefixes` | `""` | Virtual network address prefix, for example `10.0.0.0/16`. Required. |
| `azure_network_subnet_name` | `""` | Name of the subnet. Required. |
| `azure_network_subnet_address_prefix` | `""` | Subnet address prefix within the virtual network, for example `10.0.1.0/24`. Required. |
| `azure_network_tags` | `{"Ansible managed": "true"}` | Default tags applied to the virtual network. Must be a mapping. |

The role does not create resource groups, public IP addresses, network
interfaces, VMs, or Azure role assignments.

## Encrypted Data / Ansible Vault

The role does not require encrypted variables or Ansible Vault. Azure
credentials should be stored in `.azure/credentials` or supplied through the
`AZURE_*` environment variables rather than committed to the inventory.

## Tags

Available Ansible tags:

| Tag | Purpose |
| --- | --- |
| `validate_network_configuration` | Validates required settings without contacting Azure. |
| `create_network` | Validates the settings and creates the virtual network and subnet. |
| `add_tags_to_network` | Validates the settings and applies tags to the virtual network. |

## Known Limitations

- The subnet cannot be tagged because `azure.azcollection.azure_rm_subnet`
  does not support tags.
- This role creates one virtual network and one subnet per configured run.
- The subnet prefix must be a valid range within the virtual network address
  space; Azure validates this relationship.
- The role does not delete resources or manage resources inside the subnet.

## Run Ansible

Run the repository VM playbook to create the resource group, network, and VM:

```bash
ansible-playbook playbooks/create_azure_vm.yml
```

Run only the network role phases by selecting their tags:

```bash
ansible-playbook playbooks/create_azure_vm.yml --tags validate_network_configuration
ansible-playbook playbooks/create_azure_vm.yml --tags create_network
ansible-playbook playbooks/create_azure_vm.yml --tags add_tags_to_network
```

To validate the playbook without contacting Azure, run:

```bash
ansible-playbook --syntax-check playbooks/create_azure_vm.yml
```

## Deletion

Delete the resource group containing the network and all its resources with:

```bash
az group delete --name <resource_group>
```

This operation is irreversible. Verify the resource group contents before
confirming.
