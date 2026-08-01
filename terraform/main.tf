# Retrieve the active Azure client configuration (tenant ID, object ID).
data "azurerm_client_config" "current" {}

# ─── Resource Group ───────────────────────────────────────────────────────────

resource "azurerm_resource_group" "main" {
  name     = "rg-${var.project}-${var.environment}"
  location = var.location

  tags = {
    project     = var.project
    environment = var.environment
    managed_by  = "terraform"
  }
}

resource "azurerm_storage_account" "axiom_data" {
  name                     = "st${var.project}${var.environment}${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  tags = {
    project     = var.project
    environment = var.environment
    managed_by  = "terraform"
  }
}

resource "azurerm_storage_container" "specweaver_documents" {
  name                  = "specweaver-documents"
  storage_account_name  = azurerm_storage_account.axiom_data.name
  container_access_type = "private"
}

# ─── Random Secrets ───────────────────────────────────────────────────────────

resource "random_string" "suffix" {
  length  = 4
  upper   = false
  special = false
}

resource "random_password" "jwt_secret" {
  length  = 64
  special = false
}

resource "random_password" "internal_secret" {
  length  = 32
  special = false
}

# ─── Modules ──────────────────────────────────────────────────────────────────

module "acr" {
  source = "./modules/acr"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  project             = var.project
  environment         = var.environment
  suffix              = random_string.suffix.result
}

module "aks" {
  source = "./modules/aks"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  project             = var.project
  environment         = var.environment
  node_count          = var.aks_node_count
  node_vm_size        = var.aks_node_vm_size
  min_node_count      = var.aks_min_node_count
  max_node_count      = var.aks_max_node_count

  acr_id          = module.acr.acr_id
  subscription_id = var.subscription_id

  depends_on = [module.acr]
}

module "database" {
  source = "./modules/database"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  project             = var.project
  environment         = var.environment
  admin_username      = var.db_admin_username
  sku_name            = var.db_sku
  storage_mb          = var.db_storage_mb
  suffix              = random_string.suffix.result
}

module "keyvault" {
  source = "./modules/keyvault"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  project             = var.project
  environment         = var.environment
  suffix              = random_string.suffix.result

  tenant_id                      = data.azurerm_client_config.current.tenant_id
  deployer_object_id             = var.deployer_object_id
  aks_kubelet_identity_object_id = module.aks.kubelet_identity_object_id
  github_actions_sp_object_id    = var.github_actions_sp_object_id

  db_password           = module.database.admin_password
  db_connection_string  = module.database.connection_string
  jwt_secret            = random_password.jwt_secret.result
  internal_secret       = random_password.internal_secret.result
  openai_api_key        = var.openai_api_key
  azure_openai_endpoint = var.azure_openai_endpoint
  azure_openai_api_key  = var.azure_openai_api_key

  depends_on = [module.database, module.aks]
}

# ─── Lens database ────────────────────────────────────────────────────────────
# Created on the existing Flexible Server provisioned by the database module.
# Separate resource so it can be applied independently without touching
# the server configuration.
resource "azurerm_postgresql_flexible_server_database" "lens" {
  name      = "lens"
  server_id = module.database.server_id
  collation = "en_US.utf8"
  charset   = "utf8"
}
