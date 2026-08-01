#!/usr/bin/env bash
# scripts/apply-phase1-terraform.sh
#
# Automates Phase 1 Terraform updates:
#   1) terraform init
#   2) terraform validate
#   3) terraform plan
#   4) terraform apply
#   5) optional Key Vault secret-slot value updates
#
# Safe defaults:
# - uses environments/dev.tfvars unless overridden
# - prompts before apply unless --auto-approve is provided
# - prompts before setting Key Vault secret values

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
RESET='\033[0m'

info()    { echo -e "${BLUE}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*"; }
header()  { echo -e "\n${BOLD}${BLUE}== $* ==${RESET}"; }

usage() {
  cat <<'EOF'
Usage:
  ./scripts/apply-phase1-terraform.sh [options]

Options:
  -f, --var-file <path>     Terraform tfvars file (default: environments/dev.tfvars)
  -k, --state-key <value>   Terraform backend key (default: ${PROJECT_NAME}.tfstate)
      --auto-approve        Pass -auto-approve to terraform apply
  -h, --help                Show this help

Examples:
  ./scripts/apply-phase1-terraform.sh
  ./scripts/apply-phase1-terraform.sh -f environments/prod.tfvars
  ./scripts/apply-phase1-terraform.sh --auto-approve
EOF
}

VAR_FILE="environments/dev.tfvars"
AUTO_APPROVE="false"
STATE_KEY=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -f|--var-file)
      VAR_FILE="$2"
      shift 2
      ;;
    -k|--state-key)
      STATE_KEY="$2"
      shift 2
      ;;
    --auto-approve)
      AUTO_APPROVE="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      error "Unknown argument: $1"
      usage
      exit 1
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TERRAFORM_DIR="${REPO_ROOT}/terraform"

if [[ -f "${REPO_ROOT}/.deployment-config" ]]; then
  # shellcheck source=/dev/null
  source "${REPO_ROOT}/.deployment-config"
  info "Loaded .deployment-config"
else
  warn ".deployment-config not found. Falling back to current environment variables."
fi

if ! command -v terraform >/dev/null 2>&1; then
  error "terraform CLI is not installed or not on PATH."
  error "Install with: brew tap hashicorp/tap && brew install hashicorp/tap/terraform"
  exit 1
fi

if ! command -v az >/dev/null 2>&1; then
  warn "Azure CLI (az) not found. Terraform will run, but Key Vault secret update step will be skipped."
fi

if [[ ! -d "${TERRAFORM_DIR}" ]]; then
  error "Terraform directory not found: ${TERRAFORM_DIR}"
  exit 1
fi

if [[ ! -f "${TERRAFORM_DIR}/${VAR_FILE}" ]]; then
  error "Var file not found: terraform/${VAR_FILE}"
  exit 1
fi

if [[ -z "${PROJECT_NAME:-}" ]]; then
  PROJECT_NAME="aiarchitect"
  warn "PROJECT_NAME not set; using default '${PROJECT_NAME}'"
fi

if [[ -z "${STATE_KEY}" ]]; then
  STATE_KEY="${PROJECT_NAME}.tfstate"
fi

# Backward compatibility: older bootstrap fallback wrote TF_STATE_* names.
if [[ -z "${TF_BACKEND_RESOURCE_GROUP:-}" && -n "${TF_STATE_RESOURCE_GROUP:-}" ]]; then
  TF_BACKEND_RESOURCE_GROUP="${TF_STATE_RESOURCE_GROUP}"
fi

if [[ -z "${TF_BACKEND_STORAGE_ACCOUNT:-}" && -n "${TF_STATE_STORAGE_ACCOUNT:-}" ]]; then
  TF_BACKEND_STORAGE_ACCOUNT="${TF_STATE_STORAGE_ACCOUNT}"
fi

if [[ -z "${TF_BACKEND_RESOURCE_GROUP:-}" || -z "${TF_BACKEND_STORAGE_ACCOUNT:-}" ]]; then
  error "TF_BACKEND_RESOURCE_GROUP and TF_BACKEND_STORAGE_ACCOUNT must be set."
  error "Run scripts/azure-bootstrap.sh first or source .deployment-config."
  exit 1
fi

import_existing_resource_group_if_needed() {
  # Skip if already imported.
  if terraform state list | grep -q '^azurerm_resource_group.main$'; then
    info "Resource group already in Terraform state."
    return
  fi

  # Determine the exact RG name from Terraform variable values.
  local rg_name
  rg_name="$(terraform console -var-file="${VAR_FILE}" <<'EOF' | tail -n 1 | tr -d '"'
"rg-${var.project}-${var.environment}"
EOF
)"

  if [[ -z "${rg_name}" ]]; then
    warn "Could not resolve resource group name for auto-import."
    return
  fi

  if ! command -v az >/dev/null 2>&1; then
    warn "az CLI not found; skipping resource group auto-import check."
    return
  fi

  if az group show --name "${rg_name}" >/dev/null 2>&1; then
    local rg_id
    rg_id="/subscriptions/${AZURE_SUBSCRIPTION_ID}/resourceGroups/${rg_name}"
    info "Existing resource group detected without state entry. Importing ${rg_id}"
    terraform import -var-file="${VAR_FILE}" azurerm_resource_group.main "${rg_id}" >/dev/null
    success "Imported existing resource group into Terraform state."
  else
    info "Resource group ${rg_name} does not exist yet; Terraform will create it."
  fi
}

import_existing_aks_resources_if_needed() {
  if ! command -v az >/dev/null 2>&1; then
    warn "az CLI not found; skipping AKS resource auto-import checks."
    return
  fi

  if [[ -z "${AZURE_SUBSCRIPTION_ID:-}" ]]; then
    warn "AZURE_SUBSCRIPTION_ID is not set; skipping AKS resource auto-import checks."
    return
  fi

  local rg_name project_name environment_name law_name pip_name aks_name agent_pool_name
  local law_id pip_id aks_id agent_pool_id
  local aks_cluster_principal_id aks_node_resource_group

  import_existing_role_assignment_if_needed() {
    local state_address="$1"
    local scope="$2"
    local role_name="$3"
    local assignee_object_id="$4"

    if terraform state list | grep -q "^${state_address}$"; then
      info "Role assignment ${state_address} already in Terraform state."
      return
    fi

    if [[ -z "${scope}" || -z "${role_name}" || -z "${assignee_object_id}" ]]; then
      warn "Insufficient data to auto-import ${state_address}; Terraform will attempt create."
      return
    fi

    local existing_assignment_id
    existing_assignment_id="$(az role assignment list \
      --scope "${scope}" \
      --assignee-object-id "${assignee_object_id}" \
      --role "${role_name}" \
      --query '[0].id' \
      -o tsv 2>/dev/null || true)"

    if [[ -z "${existing_assignment_id}" ]]; then
      info "Role assignment ${state_address} not found in Azure; Terraform will create it."
      return
    fi

    info "Existing role assignment detected for ${state_address}. Importing ${existing_assignment_id}"
    terraform import -var-file="${VAR_FILE}" "${state_address}" "${existing_assignment_id}" >/dev/null
    success "Imported existing role assignment ${state_address} into Terraform state."
  }

  rg_name="$(terraform console -var-file="${VAR_FILE}" <<'EOF' | tail -n 1 | tr -d '"'
"rg-${var.project}-${var.environment}"
EOF
)"

  project_name="$(terraform console -var-file="${VAR_FILE}" <<'EOF' | tail -n 1 | tr -d '"'
var.project
EOF
)"

  environment_name="$(terraform console -var-file="${VAR_FILE}" <<'EOF' | tail -n 1 | tr -d '"'
var.environment
EOF
)"

  if [[ -z "${rg_name}" || -z "${project_name}" || -z "${environment_name}" ]]; then
    warn "Could not resolve AKS naming values for auto-import checks."
    return
  fi

  law_name="law-${project_name}-${environment_name}"
  pip_name="pip-${project_name}-${environment_name}-ingress"
  aks_name="aks-${project_name}-${environment_name}"
  agent_pool_name="agentpool"

  law_id="/subscriptions/${AZURE_SUBSCRIPTION_ID}/resourceGroups/${rg_name}/providers/Microsoft.OperationalInsights/workspaces/${law_name}"
  pip_id="/subscriptions/${AZURE_SUBSCRIPTION_ID}/resourceGroups/${rg_name}/providers/Microsoft.Network/publicIPAddresses/${pip_name}"
  aks_id="/subscriptions/${AZURE_SUBSCRIPTION_ID}/resourceGroups/${rg_name}/providers/Microsoft.ContainerService/managedClusters/${aks_name}"
  agent_pool_id="${aks_id}/agentPools/${agent_pool_name}"

  if terraform state list | grep -q '^module\.aks\.azurerm_kubernetes_cluster\.main$'; then
    info "AKS cluster already in Terraform state."
  elif az resource show --ids "${aks_id}" >/dev/null 2>&1; then
    info "Existing AKS cluster detected without state entry. Importing ${aks_id}"
    terraform import -var-file="${VAR_FILE}" module.aks.azurerm_kubernetes_cluster.main "${aks_id}" >/dev/null
    success "Imported existing AKS cluster into Terraform state."
  else
    info "AKS cluster ${aks_name} not found; Terraform will create it."
  fi

  if terraform state list | grep -q '^module\.aks\.azurerm_kubernetes_cluster_node_pool\.agent$'; then
    info "AKS agent node pool already in Terraform state."
  elif az resource show --ids "${agent_pool_id}" >/dev/null 2>&1; then
    info "Existing AKS agent node pool detected without state entry. Importing ${agent_pool_id}"
    terraform import -var-file="${VAR_FILE}" module.aks.azurerm_kubernetes_cluster_node_pool.agent "${agent_pool_id}" >/dev/null
    success "Imported existing AKS agent node pool into Terraform state."
  else
    info "AKS agent node pool ${agent_pool_name} not found; Terraform will create it."
  fi

  if terraform state list | grep -q '^module\.aks\.azurerm_log_analytics_workspace\.main$'; then
    info "AKS Log Analytics workspace already in Terraform state."
  elif az resource show --ids "${law_id}" >/dev/null 2>&1; then
    info "Existing Log Analytics workspace detected without state entry. Importing ${law_id}"
    terraform import -var-file="${VAR_FILE}" module.aks.azurerm_log_analytics_workspace.main "${law_id}" >/dev/null
    success "Imported existing AKS Log Analytics workspace into Terraform state."
  else
    info "AKS Log Analytics workspace ${law_name} not found; Terraform will create it."
  fi

  if terraform state list | grep -q '^module\.aks\.azurerm_public_ip\.ingress$'; then
    info "AKS ingress Public IP already in Terraform state."
  elif az resource show --ids "${pip_id}" >/dev/null 2>&1; then
    info "Existing ingress Public IP detected without state entry. Importing ${pip_id}"
    terraform import -var-file="${VAR_FILE}" module.aks.azurerm_public_ip.ingress "${pip_id}" >/dev/null
    success "Imported existing AKS ingress Public IP into Terraform state."
  else
    info "AKS ingress Public IP ${pip_name} not found; Terraform will create it."
  fi

  # Import pre-existing AKS role assignments so apply does not fail with
  # RoleAssignmentExists on long-lived environments.
  aks_cluster_principal_id="$(az aks show --resource-group "${rg_name}" --name "${aks_name}" --query 'identity.principalId' -o tsv 2>/dev/null || true)"
  aks_node_resource_group="$(az aks show --resource-group "${rg_name}" --name "${aks_name}" --query 'nodeResourceGroup' -o tsv 2>/dev/null || true)"

  if [[ -n "${aks_cluster_principal_id}" && "${aks_cluster_principal_id}" != "None" ]]; then
    import_existing_role_assignment_if_needed \
      "module.aks.azurerm_role_assignment.monitoring" \
      "${aks_id}" \
      "Monitoring Metrics Publisher" \
      "${aks_cluster_principal_id}"

    if [[ -n "${aks_node_resource_group}" && "${aks_node_resource_group}" != "None" ]]; then
      import_existing_role_assignment_if_needed \
        "module.aks.azurerm_role_assignment.aks_network_contributor" \
        "/subscriptions/${AZURE_SUBSCRIPTION_ID}/resourceGroups/${aks_node_resource_group}" \
        "Network Contributor" \
        "${aks_cluster_principal_id}"
    else
      warn "Could not resolve AKS node resource group; skipping node RG role assignment auto-import."
    fi

    import_existing_role_assignment_if_needed \
      "module.aks.azurerm_role_assignment.aks_network_contributor_main_rg" \
      "/subscriptions/${AZURE_SUBSCRIPTION_ID}/resourceGroups/${rg_name}" \
      "Network Contributor" \
      "${aks_cluster_principal_id}"
  else
    warn "Could not resolve AKS managed identity principal ID; skipping role assignment auto-import checks."
  fi
}

header "Terraform Init"
pushd "${TERRAFORM_DIR}" >/dev/null
terraform init \
  -backend-config="resource_group_name=${TF_BACKEND_RESOURCE_GROUP}" \
  -backend-config="storage_account_name=${TF_BACKEND_STORAGE_ACCOUNT}" \
  -backend-config="container_name=tfstate" \
  -backend-config="key=${STATE_KEY}"
success "terraform init complete"

header "Terraform State Guard"
import_existing_resource_group_if_needed
import_existing_aks_resources_if_needed

header "Terraform Validate"
terraform validate
success "terraform validate passed"

header "Terraform Plan"
terraform plan -var-file="${VAR_FILE}"
success "terraform plan complete"

header "Terraform Apply"
if [[ "${AUTO_APPROVE}" == "true" ]]; then
  terraform apply -var-file="${VAR_FILE}" -auto-approve
else
  terraform apply -var-file="${VAR_FILE}"
fi
success "terraform apply complete"

header "Phase 1 Output Check"
AXIOM_PLATFORM_DB_NAME="$(terraform output -raw axiom_platform_db_name 2>/dev/null || true)"
SPECWEAVER_DB_NAME="$(terraform output -raw specweaver_db_name 2>/dev/null || true)"
SPECWEAVER_DOCS_CONTAINER="$(terraform output -raw specweaver_documents_container_name 2>/dev/null || true)"
KEY_VAULT_NAME="$(terraform output -raw key_vault_name 2>/dev/null || true)"

echo "Axiom platform DB:         ${AXIOM_PLATFORM_DB_NAME:-<missing output>}"
echo "SpecWeaver DB:             ${SPECWEAVER_DB_NAME:-<missing output>}"
echo "SpecWeaver docs container: ${SPECWEAVER_DOCS_CONTAINER:-<missing output>}"

if command -v az >/dev/null 2>&1 && [[ -n "${KEY_VAULT_NAME}" ]]; then
  header "Optional: Set Key Vault Secret Slot Values"
  read -r -p "Set values for axiom-platform-jwt-secret and specweaver-jwt-secret now? (y/N): " SET_SECRETS
  if [[ "${SET_SECRETS}" =~ ^[Yy]$ ]]; then
    read -r -s -p "Value for axiom-platform-jwt-secret: " AXIOM_PLATFORM_JWT_SECRET
    echo ""
    read -r -s -p "Value for specweaver-jwt-secret: " SPECWEAVER_JWT_SECRET
    echo ""

    if [[ -n "${AXIOM_PLATFORM_JWT_SECRET}" ]]; then
      az keyvault secret set \
        --vault-name "${KEY_VAULT_NAME}" \
        --name "axiom-platform-jwt-secret" \
        --value "${AXIOM_PLATFORM_JWT_SECRET}" >/dev/null
      success "Set axiom-platform-jwt-secret"
    else
      warn "Skipped axiom-platform-jwt-secret (empty value)"
    fi

    if [[ -n "${SPECWEAVER_JWT_SECRET}" ]]; then
      az keyvault secret set \
        --vault-name "${KEY_VAULT_NAME}" \
        --name "specweaver-jwt-secret" \
        --value "${SPECWEAVER_JWT_SECRET}" >/dev/null
      success "Set specweaver-jwt-secret"
    else
      warn "Skipped specweaver-jwt-secret (empty value)"
    fi
  else
    info "Skipped Key Vault secret value update."
  fi
else
  warn "Skipping Key Vault secret update step (missing az CLI or key_vault_name output)."
fi

popd >/dev/null

header "Done"
echo "Terraform updates complete for var-file: terraform/${VAR_FILE}"
