# Generate a strong random password for the PostgreSQL admin account.
# Characters that break JDBC connection strings (@ " ' ; = & %) are excluded.
resource "random_password" "db_admin" {
  length           = 24
  special          = true
  override_special = "!#%&*()-_=+[]{}<>:?"
}

resource "azurerm_postgresql_flexible_server" "main" {
  name                = "psql-${var.project}-${var.environment}-${var.suffix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  version             = "16"

  administrator_login    = var.admin_username
  administrator_password = random_password.db_admin.result

  # Zone 1 is the default and offers the widest availability.
  zone       = "1"
  storage_mb = var.storage_mb
  sku_name   = var.sku_name

  backup_retention_days        = var.backup_retention_days
  geo_redundant_backup_enabled = var.geo_redundant_backup

  tags = {
    project     = var.project
    environment = var.environment
    managed_by  = "terraform"
  }
}

resource "azurerm_postgresql_flexible_server_database" "main" {
  name      = "aiarchitect"
  server_id = azurerm_postgresql_flexible_server.main.id
  collation = "en_US.utf8"
  charset   = "UTF8"
}

resource "azurerm_postgresql_flexible_server_database" "axiom_platform" {
  name      = "axiom_platform"
  server_id = azurerm_postgresql_flexible_server.main.id
  collation = "en_US.utf8"
  charset   = "UTF8"
}

resource "azurerm_postgresql_flexible_server_database" "specweaver" {
  name      = "specweaver"
  server_id = azurerm_postgresql_flexible_server.main.id
  collation = "en_US.utf8"
  charset   = "UTF8"
}

# In Azure's API, the range 0.0.0.0 to 0.0.0.0 means "allow connections
# from other Azure services", not "allow all internet traffic".
# This is required so AKS pods (which have Azure-internal IPs) can connect.
resource "azurerm_postgresql_flexible_server_firewall_rule" "allow_azure" {
  name             = "AllowAllAzureServices"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

resource "azurerm_postgresql_flexible_server_configuration" "max_connections" {
  name      = "max_connections"
  server_id = azurerm_postgresql_flexible_server.main.id
  value     = "100"
}

resource "azurerm_postgresql_flexible_server_configuration" "wal_level" {
  name      = "wal_level"
  server_id = azurerm_postgresql_flexible_server.main.id
  value     = "logical"
}
