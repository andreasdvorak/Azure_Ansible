# Ansible Role: environment_tests

Runs read-only checks for the Ansible controller, Azure access, and managed virtual machines.

### Features

- Verifies the configured inventory includes the `azure` group.
- Checks the Ansible Python interpreter and virtual environment.
- Checks Azure SDK imports independently from the Python environment test.
- Verifies HTTPS connectivity to Azure Resource Manager.
- Checks Azure authentication and read access to resource groups.
- Provides a separate remote connectivity and Python check for Azure virtual machines.

## Dependencies

### Required Roles

| Role | Required | Purpose |
| --- | --- | --- |
| None | - | The role has no Ansible role dependencies. |

### Optional Roles

| Role | Required | Purpose |
| --- | --- | --- |
| None | - | No optional roles are used. |

### External Requirements

- The `azure.azcollection` Ansible collection.
- The Azure collection's Python dependencies installed in the Ansible Python environment.
- Azure credentials for authentication checks, passed through `.azure/credentials` or the `AZURE_*` environment variables.
- Network access to `management.azure.com` for controller and Azure checks.
- SSH access and Python on managed hosts for the VM connectivity check.

Install the collection from the repository root with:

```bash
ansible-galaxy collection install -r requirements.yml --collections-path ./collections
```

## Supported Platforms

| Platform | Version |
| --- | --- |
| Ansible controller | Any platform supported by Ansible and the Azure collection |
| Managed hosts | Python-enabled hosts configured in the `azure` inventory group |

## Supported Clouds

| Cloud Platform | Supported |
| --- | --- |
| Azure | Yes |


## Configuration

The role uses the shared `resource_group` inventory variable when configured.
If it is empty, the Azure check lists resource groups in the active
subscription to verify authentication and read access.

| Role variable | Default | Description |
| --- | --- | --- |
| `environment_tests_checks` | `controller`, `network`, `azure` | Selects the checks to run. The combined playbook selects `hosts` for the managed-host play. |
| `resource_group` | `""` | Optional resource group name to verify in the active subscription. |

The role does not create or modify Azure resources and does not configure
credentials.

## Encrypted Data / Ansible Vault

The role does not require encrypted variables or Ansible Vault. Azure
credentials belong in `.azure/credentials` or in the `AZURE_*` environment
variables and must not be committed to the repository.

## Tags

Available tags:

| Tag | Purpose |
| --- | --- |
| `controller` | Selects the controller configuration and Python checks. |
| `network` | Selects the Azure Resource Manager HTTPS check. |
| `azure` | Selects the Azure authentication and read-access check. |
| `hosts` | Selects the managed-host connectivity check. |

## Known Limitations

- The controller check requires Python to be running inside a virtual environment.
- The Azure check verifies read access only; it does not verify permission to create or delete resources.
- The HTTPS check verifies endpoint reachability and TLS validation, not successful Azure authentication.
- The managed-host check requires SSH connectivity and a usable Python interpreter on each host.

## Run Ansible
Run the controller, network, and Azure checks:

```bash
ansible-playbook playbooks/environments_tests.yml
```

Run only the Azure authentication/read-access check:

```bash
ansible-playbook playbooks/environments_tests.yml --tags azure
```

Check SSH connectivity and remote Python on managed hosts:

```bash
ansible-playbook playbooks/environments_tests.yml --tags hosts
```

The host check uses the configured connection for `azure`; it connects to
the managed hosts rather than running locally.

## Deletion

None. This role performs read-only checks and creates no resources.
