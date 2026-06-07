# GitHub CI/CD Secrets Inventory

This file is the source of truth for GitHub repository secrets used by workflows in [./.github/workflows](../.github/workflows).

## Required secrets

| Secret | Required by workflows | Source |
|---|---|---|
| AZURE_CLIENT_ID | deploy, env-start, env-stop, env-status, env-restart-app | OIDC app registration / service principal client ID |
| AZURE_TENANT_ID | deploy, terraform, env-* | `az account show --query tenantId -o tsv` |
| AZURE_SUBSCRIPTION_ID | deploy, env-*, terraform (indirect) | `az account show --query id -o tsv` |
| AZURE_RESOURCE_GROUP | deploy, env-* | `cd terraform && terraform output -raw resource_group_name` |
| ACR_NAME | deploy, env-status | `cd terraform && terraform output -raw acr_name` |
| ACR_LOGIN_SERVER | deploy | `cd terraform && terraform output -raw acr_login_server` |
| AKS_CLUSTER_NAME | deploy, env-* | `cd terraform && terraform output -raw aks_cluster_name` |
| KEY_VAULT_NAME | deploy | `cd terraform && terraform output -raw key_vault_name` |
| KEY_VAULT_TENANT_ID | deploy | `cd terraform && terraform output -raw key_vault_tenant_id` |
| AKS_KUBELET_CLIENT_ID | deploy | `cd terraform && terraform output -raw aks_kubelet_client_id` |
| AZURE_DB_SERVER_NAME | env-start, env-stop, env-status | `cd terraform && terraform output -raw db_server_name` |
| TF_BACKEND_RESOURCE_GROUP | terraform | from [../.deployment-config](../.deployment-config): `TF_BACKEND_RESOURCE_GROUP` |
| TF_BACKEND_STORAGE_ACCOUNT | terraform | from [../.deployment-config](../.deployment-config): `TF_BACKEND_STORAGE_ACCOUNT` |
| TF_VAR_SUBSCRIPTION_ID | terraform | same as AZURE_SUBSCRIPTION_ID |
| TF_VAR_DEPLOYER_OBJECT_ID | terraform | `az ad signed-in-user show --query id -o tsv` |
| TF_VAR_OPENAI_API_KEY | terraform | OpenAI key (or set to empty if not using OpenAI) |
| AZURE_CREDENTIALS | terraform | contents of `.github-actions-credentials.json` |

## Optional secrets

| Secret | Used by workflows | Notes |
|---|---|---|
| CERT_MANAGER_EMAIL | deploy | Defaults to `admin@example.com` if unset; recommended to set a real mailbox |
| INGRESS_HOSTNAME | deploy | Optional custom domain; leave unset to use Azure-assigned FQDN |
| PROJECT_NAME | deploy | Needed only when INGRESS_HOSTNAME is empty and workflow queries Azure public IP by name |
| ENVIRONMENT | deploy | Same note as PROJECT_NAME |

## Not GitHub secrets (Phase 1)

These are Key Vault secret slots created by Terraform and should be set in Key Vault, not in GitHub:

- `axiom-platform-jwt-secret`
- `specweaver-jwt-secret`

Set them with:

```bash
cd terraform
KV_NAME="$(terraform output -raw key_vault_name)"

az keyvault secret set \
  --vault-name "$KV_NAME" \
  --name axiom-platform-jwt-secret \
  --value "<set-real-value>"

az keyvault secret set \
  --vault-name "$KV_NAME" \
  --name specweaver-jwt-secret \
  --value "<set-real-value>"
```

## One-time command pack to collect values

```bash
# From repo root
source .deployment-config

cd terraform
terraform output -raw resource_group_name
terraform output -raw acr_name
terraform output -raw acr_login_server
terraform output -raw aks_cluster_name
terraform output -raw key_vault_name
terraform output -raw key_vault_tenant_id
terraform output -raw aks_kubelet_client_id
terraform output -raw db_server_name
```
