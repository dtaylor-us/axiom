output "fqdn" {
  description = "Fully qualified domain name of the PostgreSQL Flexible Server."
  value       = azurerm_postgresql_flexible_server.main.fqdn
}

output "server_name" {
  description = "Name of the PostgreSQL Flexible Server resource."
  value       = azurerm_postgresql_flexible_server.main.name
}

output "server_id" {
  description = "Resource ID of the PostgreSQL Flexible Server. Used by database resources that reference this server."
  value       = azurerm_postgresql_flexible_server.main.id
}

output "admin_password" {
  description = "Generated administrator password for the PostgreSQL server. Sensitive."
  value       = random_password.db_admin.result
  sensitive   = true
}

output "connection_string" {
  description = "JDBC connection string for the aiarchitect database. Sensitive — contains credentials."
  value       = "jdbc:postgresql://${azurerm_postgresql_flexible_server.main.fqdn}:5432/aiarchitect?sslmode=require"
  sensitive   = true
}
