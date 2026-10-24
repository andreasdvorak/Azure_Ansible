# Introduction

This readme explains how to create an Ansible environment and how to use it.

# Prepare your environment
## Requirements
* POSIX compatible shell, eg: Bash
* Python 3
* python3-virtualenv

## Clone this repo
First clone this repo

## Create a virtual environment
It is recommended to create a virtual environemnt with all the software needed.

```bash
virtualenv -p python3 .venv
```

Enable the virtual environment
```bash
source .venv/bin/activate
```

Installation required software
```bash
pip install -r requirements.txt
ansible-galaxy collection install -r requirements.yml
```

To deactivate the virutal evironment
```bash
deactivate
```

## Ansible
Installation of Ansible is done in the Python virtual environment, with the requirements.txt.

We install `ansible-core` only, not the `ansible` package. The `ansible` package bundles
several hundred collections into the virtual environment, which would satisfy the version
constraints in requirements.yml on its own - `ansible-galaxy` would then report
"Nothing to do" and never populate ./collections. With ansible-core, requirements.yml is
the single source of truth for collection versions.

Installation of Ansible collections
```bash
ansible-galaxy collection install -r requirements.yml --collections-path ./collections
```

Installation of requirements for the Azure collection

The Azure modules need the Azure SDK for Python. Those packages are not in our
requirements.txt, they are pinned by the collection itself and have to match its
version. So install them after the collection, not before.
```bash
pip install -r ./collections/ansible_collections/azure/azcollection/requirements.txt
```

Do not put the package `azure` into requirements.txt. This meta package is deprecated
since 2020 and aborts the installation with an error, which makes the whole
`pip install -r requirements.txt` fail, so none of the other packages are installed
either. The Azure SDK consists of one package per service, for example
azure-mgmt-resource and azure-mgmt-network. The file above holds all of them.

If a module fails with "Failed to import the required Python library (azure)", the
command above has not been run in the active virtual environment. Check it with
```bash
python -c "import azure.mgmt.resource; print('ok')"
```

### Ansible Vault
Some roles are using secret data. To run Ansible for those roles you need to create the file ".vault_-pass".

The file contains the password for the decryption and encryption of all Ansible secret data we use.

To run a playbook that uses a role with secrets you need this parameter
```
--vault-password-file=.vault_pass
```

Get the content from somebody who is already using Ansible.

## Ansible key
If you want to use run Ansible the public key needs to be added in the file <ansible_user>/.ssh/authorized_keys.

The ansible_user can be ansible in older installations or the default user that AWS creates in the EC2 instance. The user name can be found in the files inventory/group_vars/<os>.yml.

If you use the default user of that AWS creates follow this:
* Add the private key file key.pem to ~/.ssh/key.pem and do

```bash
chmod 600 ~/.ssh/key.pem
```

If you use the "ansible" user follow this:
* Add you public key to the file roles/user/files/public_keys/ansible. Please make sure that your id is at the end of the string.
* create pull request
* someone else needs to run Ansible to added your key
```bash
ansible-playbook playbook/user.yml
```

Now you can run Ansible from your host.
In the inventory file hosts the ansible user is set to "ansible". Currently we run ansible with our own user. The option is
```
-e ansible_user=<username>
```

Furthermore you canset your ssh private key. The option is
```
-e ansible_ssh_private_key_file=<path and file of privatkey>
```

Default is ~/.ssh/key.pem

## Windows
ansible-vault encrypt_string 'xxxxxxxxxxxx' --name ansible_password

# Repository maintenance
## yamllint
Please check the code locally with yaml lint
```bash
yamllint .
```

## Ansible lint
Please check the code locally with Ansible lint
```bash
ansible-lint -q inventory playbooks roles
```

The message `WARNING Directory expansion discovered N file(s)` appears because
directories are passed as arguments. It is informational and does not affect
the result. To hide it, add `-q` (`ansible-lint -q inventory playbooks roles`);
the exit code and the individual violations stay, but the rule summary is not
printed. Do not run a bare `ansible-lint` instead: `inventory/` is in
`.gitignore`, so its `group_vars` and `host_vars` would no longer be checked.

## pre-commit

To do an automatic ansible-lint before the commit you need to rename the hook file

mv .git/hooks/pre-commit.sample to .git/hooks/pre-commit

## Shellcheck
Please check the Bash scripts with shellcheck
```bash
find . -type f -name "*.sh" -exec shellcheck {} +
```

# Ansible commands

## Show the Ansible inventory
### Show inventory graph

as a graph
```bash
ansible-inventory [-i inventory/hosts_provision.ini] --graph
```

as a list
```bash
ansible-inventory --list
```

Show all hosts
```bash
ansible all --list-hosts
```

With this command you can see all variable configrations for a host.
```
ansible-inventory --host <inventory host>
```

## Connection test
With this command you can test the ssh connection to all hosts:

```bash
ansible all -m ping
```

With this command you can test the ssh connection to the gitlab_servers servers:
```bash
ansible gitlab_servers -m ping
```

For Windows
```bash
ansible windows -m win_ping
```

## Verify the Ansible installation

Run the environment checker from the repository root:

```bash
python3 scripts/check_environment.py
```

The script uses `.venv` when it is available. It checks the installed Python
package and Ansible collection versions against `requirements.txt` and
`requirements.yml`, verifies Python package dependencies, runs the controller,
HTTPS, and Azure read-access checks from `playbooks/environments_tests.yml`,
checks that the Azure CLI is installed and can obtain an Azure Resource Manager
access token, and tests SSH connectivity and remote Python for the `azure`
inventory group. Sign in to the Azure CLI first with `az login`. Azure Ansible
checks require valid credentials in `.azure/credentials` or the `AZURE_*`
environment variables. A failed SSH check can indicate that a host is
unreachable or that its inventory connection settings are incomplete.

## Show facts
If you want to see the facts of a server run this:

```bash
ansible <inventory_hostname>  -m setup
```

## Usage of a tags
Show all tags and tasks
```bash
ansible-playbook [-i inventory/hosts_provisioning.ini] playbooks/<playbook> --list-tasks
```

If you just want to run the role gitlab from the playbook gitlab-servers use the tags option:
```bash
--tags gitlabserver
```

## Limit run to a hostname
Limit for host name
```bash
ansible-playbook [-i inventory/hosts_provisioning.ini] playbooks/<playbook> --limit <hostname>
```
