#!/usr/bin/env bash
# scripts/switch-to-prod-tls.sh
#
# Upgrades the Helm release from the Let's Encrypt staging issuer to the
# production issuer once the staging certificate has been verified as READY.
#
# Why two phases?
#   The Let's Encrypt production issuer imposes a rate limit of 5 duplicate
#   certificates per domain per week. Exhausting that limit during debugging
#   means waiting 7 days before a new certificate can be issued. The staging
#   issuer has much higher limits but produces a certificate from a CA that
#   browsers do not trust (so users still see a warning). This script is run
#   once — after verifying the staging cert works — to upgrade to the
#   production issuer whose CA is trusted by all browsers.
#
# Prerequisites:
#   kubectl get certificate -n ai-architect
#   → ai-architect-tls must show READY = True before running this script
#
# Idempotent: running again after a successful switch does nothing harmful.

set -euo pipefail

# ─── Colours ──────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
BOLD='\033[1m'
RESET='\033[0m'

info()    { echo -e "${BLUE}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*"; }

echo "==================================================="
echo "Switching from Let's Encrypt staging to production"
echo "==================================================="
echo ""
echo "This script upgrades the TLS certificate from the"
echo "Let's Encrypt staging CA (not trusted by browsers)"
echo "to the production CA (trusted by all browsers)."
echo ""
echo "Prerequisites:"
echo "  The staging certificate must show READY = True"
echo "  kubectl get certificate -n ai-architect"
echo ""

# Require explicit confirmation before touching the production issuer.
# Accidental use of the production issuer during debugging wastes rate-limit
# quota and forces a 7-day wait before recovery.
read -r -p "Confirm staging certificate is READY [y/N]: " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
  echo "Aborted. Run this script again once the staging cert is ready."
  exit 0
fi

# ─── Load configuration ────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ -f "${REPO_ROOT}/.deployment-config" ]]; then
  # shellcheck source=/dev/null
  source "${REPO_ROOT}/.deployment-config"
  info "Loaded .deployment-config"
else
  warn ".deployment-config not found — assuming environment variables are set."
fi

# ─── Refresh kubectl credentials ──────────────────────────────────────────────
info "Refreshing AKS credentials..."
az aks get-credentials \
  --resource-group "${AZURE_RESOURCE_GROUP}" \
  --name "${AKS_CLUSTER_NAME}" \
  --overwrite-existing

# ─── Upgrade Helm release to production issuer ────────────────────────────────
info "Upgrading Helm release to use production issuer..."

# --reuse-values preserves all other values (image tags, secrets, etc.)
# so only the TLS issuer changes. NEVER pass --reset-values here.
helm upgrade ai-architect "${REPO_ROOT}/helm/ai-architect/" \
  --namespace ai-architect \
  --reuse-values \
  --set ingress.tls.issuer=letsencrypt-prod

# ─── Delete staging certificate to force re-issuance ─────────────────────────
# cert-manager watches Certificate objects and provisions new certificates
# when the issuer annotation changes. Deleting the old certificate triggers
# immediate re-issuance rather than waiting for the existing one to expire.
info "Deleting staging certificate to trigger re-issuance with production CA..."
kubectl delete certificate ai-architect-tls \
  --namespace ai-architect \
  --ignore-not-found

echo ""
info "Waiting for production certificate to be issued (1-2 minutes)..."
echo ""

# ─── Poll for certificate readiness ───────────────────────────────────────────
# Poll every 5 seconds for up to 2 minutes (24 attempts).
for i in $(seq 1 24); do
  READY=$(kubectl get certificate ai-architect-tls \
    --namespace ai-architect \
    --output jsonpath='{.status.conditions[?(@.type=="Ready")].status}' \
    2>/dev/null || echo "False")

  if [[ "$READY" == "True" ]]; then
    success "Production certificate is READY"
    echo ""

    INGRESS_FQDN=""
    pushd "${REPO_ROOT}/terraform" > /dev/null 2>&1 || true
      INGRESS_FQDN="$(terraform output -raw ingress_fqdn 2>/dev/null || true)"
    popd > /dev/null 2>&1 || true

    echo "Your application is now served over trusted HTTPS:"
    if [[ -n "${INGRESS_FQDN}" ]]; then
      echo "  https://${INGRESS_FQDN}"
    fi
    if [[ -n "${CUSTOM_HOSTNAME:-}" ]]; then
      echo "  https://${CUSTOM_HOSTNAME}"
    fi
    echo ""
    exit 0
  fi

  echo "Attempt ${i}/24 — certificate not ready yet, waiting 5s..."
  sleep 5
done

# ─── Timeout ──────────────────────────────────────────────────────────────────
echo ""
error "Certificate did not become READY within 2 minutes."
echo ""
echo "Diagnose with:"
echo "  kubectl describe certificate ai-architect-tls -n ai-architect"
echo "  kubectl describe certificaterequest -n ai-architect"
echo "  kubectl logs -n cert-manager -l app=cert-manager --tail=50"
exit 1
