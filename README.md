# Azure_Ansible
Setup Microsoft Azure with Ansible

# Prepation
## Inventory
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
