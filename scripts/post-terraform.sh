#!/usr/bin/env bash
# scripts/post-terraform.sh
#
# Runs after `terraform apply` to install Kubernetes components that
# Terraform cannot manage directly:
#   - nginx ingress controller
#   - cert-manager
#   - Azure Key Vault CSI driver
#   - ai-architect application namespace
#
# Idempotent — uses `helm upgrade --install` throughout.
# Safe to re-run if any step was interrupted.

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

# Determine the repo root (the directory containing this script's parent).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ─── Step 1: Source .deployment-config if present ─────────────────────────────
header "Step 1 — Loading configuration"

if [[ -f "${REPO_ROOT}/.deployment-config" ]]; then
  # shellcheck source=/dev/null
  source "${REPO_ROOT}/.deployment-config"
  success "Loaded .deployment-config"
else
  warn ".deployment-config not found — assuming environment variables are set."
fi

# ─── Prompt for LETSENCRYPT_EMAIL ─────────────────────────────────────────────
# Let's Encrypt requires a valid email address at registration time.
# The same address receives certificate expiry warnings (60- and 14-days notice)
# so use a real, monitored inbox.
if [[ -z "${LETSENCRYPT_EMAIL:-}" ]]; then
  read -r -p "Enter email address for Let's Encrypt notifications: " LETSENCRYPT_EMAIL
  export LETSENCRYPT_EMAIL
fi

if [[ -z "${LETSENCRYPT_EMAIL:-}" ]]; then
  error "LETSENCRYPT_EMAIL is required for TLS certificate issuance."
  error "Re-run with: export LETSENCRYPT_EMAIL=you@example.com && ./scripts/post-terraform.sh"
  exit 1
fi

info "Let's Encrypt email: ${LETSENCRYPT_EMAIL}"

# ─── Step 2: Configure kubectl ────────────────────────────────────────────────
header "Step 2 — Configuring kubectl"

info "Fetching AKS credentials from Terraform output..."
pushd "${REPO_ROOT}/terraform" > /dev/null
  GET_CREDENTIALS_CMD="$(terraform output -raw get_credentials_command 2>/dev/null || true)"
popd > /dev/null

if [[ -z "${GET_CREDENTIALS_CMD}" ]]; then
  error "Could not read get_credentials_command from Terraform output."
  error "Ensure 'terraform apply' has completed successfully before running this script."
  exit 1
fi

info "Running: ${GET_CREDENTIALS_CMD}"
eval "${GET_CREDENTIALS_CMD}"
success "kubectl configured for AKS cluster."

# ─── Step 3: Install nginx ingress controller ─────────────────────────────────
header "Step 3 — Installing nginx ingress controller"

# Read the static public IP and related values from Terraform output.
# The static IP must exist before installing nginx so that Azure associates
# the load balancer with the Terraform-managed IP rather than creating a
# new dynamic one (which would change on every redeployment and break
# Let's Encrypt certificate bindings).
pushd "${REPO_ROOT}/terraform" > /dev/null
  INGRESS_IP="$(terraform output -raw ingress_ip 2>/dev/null || true)"
  INGRESS_IP_ID="$(terraform output -raw ingress_public_ip_id 2>/dev/null || true)"
  RESOURCE_GROUP="$(terraform output -raw resource_group_name 2>/dev/null || true)"
  INGRESS_FQDN="$(terraform output -raw ingress_fqdn 2>/dev/null || true)"
popd > /dev/null

if [[ -z "${INGRESS_IP}" ]]; then
  error "Could not read ingress_ip from terraform output."
  error "Run 'terraform apply' first and ensure the ingress public IP was created."
  exit 1
fi

info "Using static ingress IP: ${INGRESS_IP}"
info "Ingress FQDN:            ${INGRESS_FQDN}"

helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx 2>/dev/null || true
helm repo update

helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.service.loadBalancerIP="${INGRESS_IP}" \
  --set "controller.service.annotations.service\.beta\.kubernetes\.io/azure-load-balancer-resource-group=${RESOURCE_GROUP}" \
  --set "controller.service.annotations.service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path=/healthz" \
  --set "controller.service.annotations.service\.beta\.kubernetes\.io/azure-pip-name=pip-${PROJECT_NAME}-${ENVIRONMENT}-ingress" \
  --set controller.config.use-forwarded-headers="true" \
  --set controller.config.proxy-buffer-size="128k" \
  --wait --timeout 5m

success "nginx ingress controller installed with static IP ${INGRESS_IP}."

# ─── Step 4: Install cert-manager ─────────────────────────────────────────────
header "Step 4 — Installing cert-manager"

helm repo add jetstack https://charts.jetstack.io 2>/dev/null || true
helm repo update

helm upgrade --install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --set installCRDs=true \
  --set global.leaderElection.namespace=cert-manager \
  --wait --timeout 5m

info "Waiting for cert-manager pods to be ready..."
kubectl wait --namespace cert-manager \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/instance=cert-manager \
  --timeout=120s

success "cert-manager installed."

# ─── Step 4b: Create cert-manager ClusterIssuers ─────────────────────────────
header "Step 4b — Creating Let's Encrypt ClusterIssuers"

# Staging issuer is used first to verify the ACME flow works without consuming
# the Let's Encrypt production rate limit (5 duplicate certificates per week).
# Once the staging certificate shows READY, run scripts/switch-to-prod-tls.sh
# to upgrade to the production issuer whose CA is trusted by all browsers.
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-staging
spec:
  acme:
    server: https://acme-staging-v02.api.letsencrypt.org/directory
    email: ${LETSENCRYPT_EMAIL}
    privateKeySecretRef:
      name: letsencrypt-staging-key
    solvers:
      - http01:
          ingress:
            class: nginx
EOF

# Production issuer — activate once staging certificate is verified READY.
# Never use the production issuer for debugging; exhausting rate limits means
# waiting 7 days before a new certificate can be issued.
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: ${LETSENCRYPT_EMAIL}
    privateKeySecretRef:
      name: letsencrypt-prod-key
    solvers:
      - http01:
          ingress:
            class: nginx
EOF

success "ClusterIssuers created: letsencrypt-staging, letsencrypt-prod."

# ─── Step 5: Verify Secrets Store CSI driver (managed by AKS add-on) ────────
header "Step 5 — Verifying Secrets Store CSI driver (AKS add-on)"

# The AKS key_vault_secrets_provider add-on manages both the core CSI driver
# and the Azure provider DaemonSets. No separate Helm install is needed or safe.
kubectl get csidriver secrets-store.csi.k8s.io
kubectl get daemonset -n kube-system aks-secrets-store-provider-azure
success "Secrets Store CSI driver and Azure provider are present (AKS add-on)."

# ─── Step 6: Create application namespace ────────────────────────────────────
header "Step 6 — Creating application namespace"

# --dry-run=client + apply is idempotent because it will not error if the
# namespace already exists — it simply re-applies the unchanged object.
kubectl create namespace ai-architect --dry-run=client -o yaml \
  | kubectl apply -f -

success "Namespace 'ai-architect' ready."

# ─── Step 7: Wait for ingress external IP ─────────────────────────────────────
header "Step 7 — Waiting for ingress external IP"

# Maximum wait time: 3 minutes (18 polls × 10 seconds each)
MAX_POLLS=18
POLL_INTERVAL=10
EXTERNAL_IP=""

info "Waiting for the Azure Load Balancer to assign an external IP..."
info "(This can take 1–3 minutes)"

for ((i = 1; i <= MAX_POLLS; i++)); do
  EXTERNAL_IP="$(kubectl get service ingress-nginx-controller \
    --namespace ingress-nginx \
    --template '{{range .status.loadBalancer.ingress}}{{.ip}}{{end}}' 2>/dev/null || true)"

  if [[ -n "$EXTERNAL_IP" ]]; then
    break
  fi

  printf "."
  sleep "$POLL_INTERVAL"
done
echo ""  # newline after progress dots

if [[ -z "$EXTERNAL_IP" ]]; then
  warn "Timed out waiting for external IP after $((MAX_POLLS * POLL_INTERVAL)) seconds."
  warn "The Load Balancer may still be provisioning. Check again with:"
  warn "  kubectl get service ingress-nginx-controller -n ingress-nginx"
else
  success "External IP assigned: ${EXTERNAL_IP}"
fi

# ─── Step 8: Print final summary ──────────────────────────────────────────────
header "Step 8 — Summary"

echo ""
echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════════════════════╗${RESET}"
echo -e "${GREEN}${BOLD}║           Post-Terraform setup completed!                    ║${RESET}"
echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════════════════════╝${RESET}"
echo ""
echo -e "${BOLD}Installed:${RESET}"
echo "  ✓ nginx Ingress Controller  (namespace: ingress-nginx)"
echo "  ✓ cert-manager              (namespace: cert-manager)"
echo "  ✓ Azure Key Vault CSI       (namespace: kube-system)"
echo "  ✓ Application namespace:    ai-architect"
echo ""

if [[ -n "$EXTERNAL_IP" ]]; then
  echo -e "${BOLD}Your application entry point:${RESET}"
  echo ""
  echo "  External IP:   ${EXTERNAL_IP}"
  echo ""
  echo "  If you have a domain, create an A record:"
  echo "    Host: aiarchitect  (or @)  →  IP: ${EXTERNAL_IP}"
  echo ""
  echo ""
  if [[ -n "${INGRESS_FQDN:-}" ]]; then
    echo "  Azure-assigned FQDN (use this if you have no custom domain):"
    echo "    https://${INGRESS_FQDN}"
  fi
  echo ""
  echo "  If you have a custom domain, create a DNS A record:"
  echo "    Host: aiarchitect  (or @)  →  IP: ${EXTERNAL_IP}"
fi

echo -e "${BOLD}TLS certificate status:${RESET}"
echo ""
echo "  The staging certificate will be issued in 1-2 minutes."
echo "  Check status:"
echo "    kubectl get certificate -n ai-architect"
echo "    kubectl describe certificate ai-architect-tls -n ai-architect"
echo ""
echo "  Once staging certificate shows READY = True, switch to production:"
echo "    ./scripts/switch-to-prod-tls.sh"
echo ""
echo -e "${BOLD}Next step:${RESET}"
echo "  Add the GitHub Secrets listed by the bootstrap script, then push to main:"
echo "    git add ."
echo "    git commit -m \"Add deployment configuration\""
echo "    git push origin main"
echo ""
echo "  The CI/CD pipeline will build and deploy your application automatically."
echo ""
