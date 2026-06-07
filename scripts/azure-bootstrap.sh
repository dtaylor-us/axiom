#!/usr/bin/env bash
# scripts/azure-bootstrap.sh
#
# One-time Azure setup for the Axiom deployment.
# Run this script before any Terraform commands.
#
# What it does:
#   1. Verifies required CLI tools are installed
#   2. Ensures the user is logged in to Azure
#   3. Prompts for configuration values
#   4. Creates Terraform remote-state storage
#   5. Creates the GitHub Actions service principal
#   6. Writes .deployment-config for use by other scripts
#
# Idempotent — running twice will detect existing resources and skip them.

set -euo pipefail

# ─── Colours ──────────────────────────────────────────────────────────────────
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
header()  { echo -e "\n${BOLD}${BLUE}══ $* ══${RESET}"; }

# ─── Step 1: Check required tools ─────────────────────────────────────────────
header "Step 1 — Checking required tools"

check_tool() {
  local tool="$1"
  local install_mac="$2"
  local install_ubuntu="$3"

  if ! command -v "$tool" &>/dev/null; then
    error "Required tool '${tool}' is not installed."
    echo    "  macOS:  ${install_mac}"
    echo    "  Ubuntu: ${install_ubuntu}"
    return 1
  fi
  success "${tool} found: $(command -v "$tool")"
  return 0
}

MISSING_TOOLS=0

check_tool "az"        "brew install azure-cli"                    "curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash" || MISSING_TOOLS=$((MISSING_TOOLS + 1))
check_tool "terraform" "brew tap hashicorp/tap && brew install hashicorp/tap/terraform" "sudo apt-get install -y gnupg software-properties-common && wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg && echo \"deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com \$(lsb_release -cs) main\" | sudo tee /etc/apt/sources.list.d/hashicorp.list && sudo apt update && sudo apt install terraform" || MISSING_TOOLS=$((MISSING_TOOLS + 1))
check_tool "kubectl"   "brew install kubectl"                      "sudo az aks install-cli" || MISSING_TOOLS=$((MISSING_TOOLS + 1))
check_tool "helm"      "brew install helm"                         "curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash" || MISSING_TOOLS=$((MISSING_TOOLS + 1))

if [[ $MISSING_TOOLS -gt 0 ]]; then
  error "${MISSING_TOOLS} required tool(s) are missing. Install them and re-run this script."
  exit 1
fi

# ─── Step 2: Azure login ───────────────────────────────────────────────────────
header "Step 2 — Checking Azure login"

if ! az account show &>/dev/null; then
  warn "Not logged in to Azure. Starting interactive login..."
  az login
fi
success "Logged in to Azure as: $(az account show --query user.name -o tsv)"

# ─── Step 3: Prompt for configuration values ──────────────────────────────────
header "Step 3 — Gathering configuration values"

# Show available Azure locations to help the user choose
echo ""
echo "Available Azure locations (commonly used):"
echo "  eastus          East US"
echo "  eastus2         East US 2"
echo "  westus2         West US 2"
echo "  westeurope      West Europe"
echo "  northeurope     North Europe"
echo "  uksouth         UK South"
echo "  ukwest          UK West"
echo "  australiaeast   Australia East"
echo "  southeastasia   Southeast Asia"
echo "  japaneast       Japan East"
echo "  canadacentral   Canada Central"
echo "(Full list: az account list-locations -o table)"
echo ""

prompt_with_default() {
  local var_name="$1"
  local prompt_text="$2"
  local default_value="$3"
  local is_secret="${4:-false}"

  if [[ -n "${!var_name:-}" ]]; then
    info "${var_name} already set in environment: ${!var_name}"
    return
  fi

  if [[ "$is_secret" == "true" ]]; then
    # Read sensitive input without echo
    read -r -s -p "${prompt_text} [default: ${default_value}]: " user_input
    echo ""
  else
    read -r -p "${prompt_text} [default: ${default_value}]: " user_input
  fi

  if [[ -z "${user_input}" ]]; then
    eval "export ${var_name}='${default_value}'"
  else
    eval "export ${var_name}='${user_input}'"
  fi
}

# Subscription — show available subscriptions first
if [[ -z "${AZURE_SUBSCRIPTION_ID:-}" ]]; then
  echo ""
  echo "Your Azure subscriptions:"
  az account list --query "[].{Name:name, ID:id, State:state}" -o table
  echo ""
  prompt_with_default "AZURE_SUBSCRIPTION_ID" "Enter your Azure subscription ID" ""
fi

if [[ -z "${AZURE_SUBSCRIPTION_ID}" ]]; then
  error "Subscription ID is required."
  exit 1
fi

prompt_with_default "AZURE_LOCATION"  "Azure location"  "uksouth"
prompt_with_default "PROJECT_NAME"    "Project name (lowercase alphanumeric, max 12 chars)" "aiarchitect"
prompt_with_default "ENVIRONMENT"     "Environment (dev or prod)" "dev"

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  read -r -p "OpenAI API key (press Enter to skip): " OPENAI_API_KEY
  export OPENAI_API_KEY
fi

# Let's Encrypt email — required for TLS certificate issuance.
# This address receives certificate expiry warnings at 60 and 14 days before
# the 90-day expiry. Use a real, monitored inbox.
if [[ -z "${LETSENCRYPT_EMAIL:-}" ]]; then
  read -r -p "Email for Let's Encrypt TLS certificates (required): " LETSENCRYPT_EMAIL
  export LETSENCRYPT_EMAIL
fi

if [[ -z "${LETSENCRYPT_EMAIL:-}" ]]; then
  error "LETSENCRYPT_EMAIL is required for TLS certificate issuance."
  exit 1
fi

# Validate project name — must be lowercase alphanumeric, max 12 chars
if ! echo "$PROJECT_NAME" | grep -qE '^[a-z0-9]{1,12}$'; then
  error "PROJECT_NAME must be lowercase alphanumeric only, maximum 12 characters. Got: '${PROJECT_NAME}'"
  exit 1
fi

info "Using subscription: ${AZURE_SUBSCRIPTION_ID}"
info "Using location:     ${AZURE_LOCATION}"
info "Using project:      ${PROJECT_NAME}"
info "Using environment:  ${ENVIRONMENT}"

# ─── Step 4: Set active subscription ──────────────────────────────────────────
header "Step 4 — Setting active subscription"

az account set --subscription "$AZURE_SUBSCRIPTION_ID"
success "Active subscription set to: ${AZURE_SUBSCRIPTION_ID}"

# ─── Step 5: Create Terraform state storage ────────────────────────────────────
header "Step 5 — Creating Terraform state storage"

TF_STATE_RESOURCE_GROUP="rg-${PROJECT_NAME}-tfstate"

# Storage account names: lowercase alphanumeric only, 3-24 chars.
# Derive and truncate to 24 chars.
RAW_SA_NAME="st${PROJECT_NAME}tfstate"
TF_STATE_STORAGE_ACCOUNT="${RAW_SA_NAME:0:24}"
TF_STATE_CONTAINER="tfstate"

# Create resource group (idempotent)
if az group show --name "$TF_STATE_RESOURCE_GROUP" &>/dev/null; then
  info "Resource group '${TF_STATE_RESOURCE_GROUP}' already exists — skipping."
else
  info "Creating resource group '${TF_STATE_RESOURCE_GROUP}'..."
  az group create \
    --name "$TF_STATE_RESOURCE_GROUP" \
    --location "$AZURE_LOCATION" \
    --output none
  success "Resource group created."
fi

# Create storage account (idempotent)
if az storage account show \
    --name "$TF_STATE_STORAGE_ACCOUNT" \
    --resource-group "$TF_STATE_RESOURCE_GROUP" &>/dev/null; then
  info "Storage account '${TF_STATE_STORAGE_ACCOUNT}' already exists — skipping."
else
  info "Creating storage account '${TF_STATE_STORAGE_ACCOUNT}'..."
  az storage account create \
    --name "$TF_STATE_STORAGE_ACCOUNT" \
    --resource-group "$TF_STATE_RESOURCE_GROUP" \
    --location "$AZURE_LOCATION" \
    --sku Standard_LRS \
    --kind StorageV2 \
    --min-tls-version TLS1_2 \
    --allow-blob-public-access false \
    --output none
  success "Storage account created."
fi

# Create blob container (idempotent)
if az storage container show \
    --name "$TF_STATE_CONTAINER" \
    --account-name "$TF_STATE_STORAGE_ACCOUNT" \
    --auth-mode login &>/dev/null 2>&1; then
  info "Blob container '${TF_STATE_CONTAINER}' already exists — skipping."
else
  info "Creating blob container '${TF_STATE_CONTAINER}'..."
  az storage container create \
    --name "$TF_STATE_CONTAINER" \
    --account-name "$TF_STATE_STORAGE_ACCOUNT" \
    --auth-mode login \
    --output none
  success "Blob container created."
fi

# ─── Step 6: Get current user object ID ───────────────────────────────────────
header "Step 6 — Retrieving deployer object ID"

DEPLOYER_OBJECT_ID="$(az ad signed-in-user show --query id -o tsv)"
success "Deployer object ID: ${DEPLOYER_OBJECT_ID}"

# ─── Step 7: Create GitHub Actions service principal ──────────────────────────
header "Step 7 — Creating GitHub Actions service principal"

SP_NAME="sp-${PROJECT_NAME}-github"
CREDENTIALS_FILE=".github-actions-credentials.json"

if az ad sp list --display-name "$SP_NAME" --query '[0].appId' -o tsv 2>/dev/null | grep -q .; then
  warn "Service principal '${SP_NAME}' already exists."
  warn "To regenerate credentials, delete it first with:"
  warn "  az ad sp delete --id \$(az ad sp list --display-name ${SP_NAME} --query '[0].appId' -o tsv)"
  warn "Skipping service principal creation. Existing credentials file retained if present."
else
  info "Creating service principal '${SP_NAME}'..."
  az ad sp create-for-rbac \
    --name "$SP_NAME" \
    --role Contributor \
    --scopes "/subscriptions/${AZURE_SUBSCRIPTION_ID}" \
    --sdk-auth \
    > "$CREDENTIALS_FILE"
  success "Service principal created. Credentials saved to ${CREDENTIALS_FILE}"
fi

# Extract the SP object ID for use in Key Vault role assignments
GITHUB_SP_OBJECT_ID="$(az ad sp list --display-name "$SP_NAME" \
  --query '[0].id' -o tsv 2>/dev/null || echo "")"

if [[ -n "$GITHUB_SP_OBJECT_ID" ]]; then
  success "GitHub Actions SP object ID: ${GITHUB_SP_OBJECT_ID}"
else
  warn "Could not retrieve SP object ID — Key Vault access for GitHub Actions must be granted manually."
fi

# ─── Step 8: Grant AcrPush to service principal (best effort) ─────────────────
header "Step 8 — Granting AcrPush to service principal (best effort)"

ACR_NAME="acr${PROJECT_NAME}${ENVIRONMENT}"
ACR_RESOURCE_ID="/subscriptions/${AZURE_SUBSCRIPTION_ID}/resourceGroups/rg-${PROJECT_NAME}-${ENVIRONMENT}/providers/Microsoft.ContainerRegistry/registries/${ACR_NAME}"

if [[ -n "$GITHUB_SP_OBJECT_ID" ]]; then
  if az role assignment create \
      --assignee "$GITHUB_SP_OBJECT_ID" \
      --role "AcrPush" \
      --scope "$ACR_RESOURCE_ID" \
      --output none 2>/dev/null; then
    success "AcrPush role assigned to GitHub Actions SP."
  else
    warn "Could not assign AcrPush role now — ACR may not exist yet."
    warn "Re-run this script after 'terraform apply' to grant AcrPush."
  fi
else
  warn "Skipping AcrPush assignment — SP object ID not available."
fi

# ─── Step 9: Write .deployment-config ─────────────────────────────────────────
header "Step 9 — Writing .deployment-config"

cat > .deployment-config <<EOF
# Auto-generated by scripts/azure-bootstrap.sh
# Source this file to restore configuration:
#   source .deployment-config
# This file is in .gitignore — never commit it.

export AZURE_SUBSCRIPTION_ID="${AZURE_SUBSCRIPTION_ID}"
export AZURE_LOCATION="${AZURE_LOCATION}"
export PROJECT_NAME="${PROJECT_NAME}"
export ENVIRONMENT="${ENVIRONMENT}"
export DEPLOYER_OBJECT_ID="${DEPLOYER_OBJECT_ID}"
export TF_STATE_RESOURCE_GROUP="${TF_STATE_RESOURCE_GROUP}"
export TF_STATE_STORAGE_ACCOUNT="${TF_STATE_STORAGE_ACCOUNT}"
export GITHUB_SP_OBJECT_ID="${GITHUB_SP_OBJECT_ID:-}"
export LETSENCRYPT_EMAIL="${LETSENCRYPT_EMAIL}"
EOF

success ".deployment-config written."

# ─── Step 10: Print summary ────────────────────────────────────────────────────
header "Step 10 — Summary"

echo ""
echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════════════════════╗${RESET}"
echo -e "${GREEN}${BOLD}║              Bootstrap completed successfully!               ║${RESET}"
echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════════════════════╝${RESET}"
echo ""
echo -e "${BOLD}Resources created:${RESET}"
echo "  • Resource group:    ${TF_STATE_RESOURCE_GROUP}"
echo "  • Storage account:   ${TF_STATE_STORAGE_ACCOUNT}"
echo "  • Blob container:    ${TF_STATE_CONTAINER}"
echo "  • Service principal: ${SP_NAME}"
echo ""
echo -e "${BOLD}Local files created:${RESET}"
echo "  • .deployment-config                 (all config values — source this in new shells)"
echo "  • .github-actions-credentials.json  (GitHub Actions credentials — keep secret)"
echo ""
echo -e "${YELLOW}${BOLD}══ GitHub Secrets to add ══${RESET}"
echo ""
echo "Go to: GitHub → Your Repo → Settings → Secrets and variables → Actions"
echo "Add each secret below:"
echo ""

AZURE_TENANT_ID="$(az account show --query tenantId -o tsv)"

if [[ -f "$CREDENTIALS_FILE" ]]; then
  echo -e "${BOLD}Secret: AZURE_CREDENTIALS${RESET}"
  echo "Value:  (full contents of .github-actions-credentials.json)"
  echo "        cat .github-actions-credentials.json"
  echo ""
fi

echo -e "${BOLD}Secret: AZURE_SUBSCRIPTION_ID${RESET}"
echo "Value:  ${AZURE_SUBSCRIPTION_ID}"
echo ""
echo -e "${BOLD}Secret: AZURE_TENANT_ID${RESET}"
echo "Value:  ${AZURE_TENANT_ID}"
echo ""
echo -e "${BOLD}Secret: TF_BACKEND_RESOURCE_GROUP${RESET}"
echo "Value:  ${TF_STATE_RESOURCE_GROUP}"
echo ""
echo -e "${BOLD}Secret: TF_BACKEND_STORAGE_ACCOUNT${RESET}"
echo "Value:  ${TF_STATE_STORAGE_ACCOUNT}"
echo ""
echo -e "${BOLD}Secret: TF_VAR_SUBSCRIPTION_ID${RESET}"
echo "Value:  ${AZURE_SUBSCRIPTION_ID}"
echo ""
echo -e "${BOLD}Secret: TF_VAR_DEPLOYER_OBJECT_ID${RESET}"
echo "Value:  ${DEPLOYER_OBJECT_ID}"
echo ""

if [[ -n "${OPENAI_API_KEY:-}" ]]; then
  echo -e "${BOLD}Secret: TF_VAR_OPENAI_API_KEY${RESET}"
  echo "Value:  ${OPENAI_API_KEY}"
  echo ""
fi

echo -e "${YELLOW}The following secrets will be available after terraform apply:${RESET}"
echo "  AZURE_RESOURCE_GROUP, ACR_LOGIN_SERVER, ACR_NAME,"
echo "  AKS_CLUSTER_NAME, KEY_VAULT_NAME, KEY_VAULT_TENANT_ID,"
echo "  AKS_KUBELET_CLIENT_ID"
echo "(Run: cd terraform && terraform output  to get these values)"
echo ""
echo -e "${BOLD}Next step:${RESET}"
echo "  1. Copy the variable example file:"
echo "       cp terraform/environments/dev.tfvars.example terraform/environments/dev.tfvars"
echo "  2. Fill in your values in dev.tfvars"
echo "  3. Run Terraform:"
echo "       cd terraform"
echo "       terraform init \\"
echo "         -backend-config=\"resource_group_name=${TF_STATE_RESOURCE_GROUP}\" \\"
echo "         -backend-config=\"storage_account_name=${TF_STATE_STORAGE_ACCOUNT}\" \\"
echo "         -backend-config=\"container_name=${TF_STATE_CONTAINER}\" \\"
echo "         -backend-config=\"key=aiarchitect.tfstate\""
echo "       terraform apply -var-file=environments/dev.tfvars"
echo ""
