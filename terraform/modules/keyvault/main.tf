resource "azurerm_key_vault" "main" {
  name                = "kv-${var.project}-${var.environment}-${var.suffix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  tenant_id           = var.tenant_id
  sku_name            = "standard"

  # RBAC authorization replaces legacy access policies — simpler and more auditable.
  enable_rbac_authorization = true

  # 7-day soft-delete window provides safety against accidental destruction.
  # purge_protection is disabled by default for dev so `terraform destroy` works.
  soft_delete_retention_days = 7
  purge_protection_enabled   = var.purge_protection

  tags = {
    project     = var.project
    environment = var.environment
    managed_by  = "terraform"
  }
}

# ─── Role Assignments ─────────────────────────────────────────────────────────

# The deployer (the person or CI runner executing Terraform) needs
# Key Vault Administrator to write secrets during apply.
resource "azurerm_role_assignment" "deployer_admin" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = var.deployer_object_id
}

# The AKS kubelet identity reads secrets at pod start-up via the CSI driver.
resource "azurerm_role_assignment" "aks_secrets_user" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = var.aks_kubelet_identity_object_id
}

# Optional: grant the GitHub Actions service principal read access so
# CI/CD pipelines can fetch secrets directly if needed.
resource "azurerm_role_assignment" "github_secrets_user" {
  count = var.github_actions_sp_object_id != "" ? 1 : 0

  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = var.github_actions_sp_object_id
}

# ─── Secrets ──────────────────────────────────────────────────────────────────
# Each secret depends on deployer_admin to avoid the race condition where
# the secret write is attempted before the role assignment has propagated.

resource "azurerm_key_vault_secret" "db_password" {
  name         = "db-password"
  value        = var.db_password
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.deployer_admin]
}

resource "azurerm_key_vault_secret" "db_connection_string" {
  name         = "db-connection-string"
  value        = var.db_connection_string
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.deployer_admin]
}

resource "azurerm_key_vault_secret" "jwt_secret" {
  name         = "jwt-secret"
  value        = var.jwt_secret
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.deployer_admin]
}

resource "azurerm_key_vault_secret" "internal_secret" {
  name         = "internal-secret"
  value        = var.internal_secret
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.deployer_admin]
}

resource "azurerm_key_vault_secret" "openai_api_key" {
  count = var.openai_api_key != "" ? 1 : 0

  name         = "openai-api-key"
  value        = var.openai_api_key
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.deployer_admin]
}

resource "azurerm_key_vault_secret" "azure_openai_endpoint" {
  count = var.azure_openai_endpoint != "" ? 1 : 0

  name         = "azure-openai-endpoint"
  value        = var.azure_openai_endpoint
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.deployer_admin]
}

resource "azurerm_key_vault_secret" "azure_openai_api_key" {
  count = var.azure_openai_api_key != "" ? 1 : 0

  name         = "azure-openai-api-key"
  value        = var.azure_openai_api_key
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.deployer_admin]
}

resource "azurerm_key_vault_secret" "axiom_platform_jwt_secret" {
  name         = "axiom-platform-jwt-secret"
  value        = "placeholder-set-after-provisioning"
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.deployer_admin]

  lifecycle {
    ignore_changes = [value]
  }
}

resource "azurerm_key_vault_secret" "specweaver_jwt_secret" {
  name         = "specweaver-jwt-secret"
  value        = "placeholder-set-after-provisioning"
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.deployer_admin]

  lifecycle {
    ignore_changes = [value]
  }
}
