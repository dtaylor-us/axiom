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
