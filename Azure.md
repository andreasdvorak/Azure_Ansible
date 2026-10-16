# Azure
Setup Microsoft Azure

# Prepation
## Azure CLI
Installation of Azure CLI

    curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

### az login
To run the terraform apply you first need to login at Azure

    az login

### Get Azure Regions

    az account list-locations -o table

### List Subscriptions

    az account list

### Show Subscription

    az account show

## Service Principals
I am using a service principal with high permissions for the administration of Identity Management and a second principal with lower permissions for resource managemant.

### Service principal Identity Management
This configuration needs to be done with Global Administrator.

To access Azure with Ansible you need a client_id and client_secret.

Create a Service Principal

    az ad sp create-for-rbac --name "ansible-sp"

        {
    "appId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",         # → Client ID
    "displayName": "ansible-sp",
    "password": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",       # → Client Secret
    "tenant": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"          # → Tenant ID
    }

    APP_ID="<appId>"

In the Azure portal the SP can be seen in Microsoft Entra ID -> App registrations

Get Permission IDs

    az ad sp show --id 00000003-0000-0000-c000-000000000000 --query "oauth2PermissionScopes"

Get Role IDs

    az ad sp show --id 00000003-0000-0000-c000-000000000000 --query "appRoles"


### Add role contributor
You need to add the role contributor to the service principal on the subscription level

```
SUBSCRIPTION_ID="<deine-Subscription-ID>"
APP_ID="<Service-Principal-Client-ID>"

az role assignment create \
  --assignee $APP_ID \
  --role "Contributor" \
  --scope /subscriptions/$SUBSCRIPTION_ID
```

To see it in the Azure Portal got to the subscription -> Access control (IAM) -> Role assignments

### Configuration of credentials for Ansible
Put the Azure credentials in the file .azure/credentials
```
[default]
client_id=xxxxxxxxxx
secret=xxxxxxxxxxxx
subscription_id=xxxxxxxxxxxxxxxx
tenant=xxxxxxxxxxxxx
```

Or
```
export AZURE_CLIENT_ID="<appId>"
export AZURE_SECRET="<password>"
export AZURE_TENANT="<tenant>"
export AZURE_SUBSCRIPTION_ID="<subscription_id>"
```