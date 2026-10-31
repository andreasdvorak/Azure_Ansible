[![Azure](https://img.shields.io/badge/Azure-0078D4?logo=microsoftazure&logoColor=white)](https://azure.microsoft.com/)
[![Ansible](https://img.shields.io/badge/Ansible-EE0000?logo=ansible&logoColor=white)](https://www.ansible.com/)
![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)

# Azure_Ansible

Setup Microsoft Azure with Ansible

# Prepation

## Prepare Azure

To configure Azure for Ansible please follow this guide:

[Azure](Azure.md)


## Prepare of Ansible

To user Ansible please follow this guide:

[Ansible](Ansible.md)

## Prepare Inventory
Create these directorys and files

```
inventory/group_vars/all.yml
inventory/host_vars/localhost
```

You need at least this file with the content below.
```
inventory/hosts.ini

[local]
localhost ansible_connection=local

```
