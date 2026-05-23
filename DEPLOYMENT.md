# Deployment Guide : AI Architect Assistant

## What this guide covers

Terraform creates the Azure infrastructure once. GitHub Actions deploys your
application automatically on every merge to `main`. You only need to provide
credentials and run two scripts — the rest is automated.

Estimated total setup time: **45–60 minutes**.

---

## Prerequisites

### Tools required

| Tool | Install (macOS) | Install (Ubuntu) | Verify |
|---|---|---|---|
| Azure CLI | `brew install azure-cli` | `curl -sL https://aka.ms/InstallAzureCLIDeb \| sudo bash` | `az --version` |
| Terraform | `brew tap hashicorp/tap && brew install hashicorp/tap/terraform` | See [terraform.io/downloads](https://developer.hashicorp.com/terraform/downloads) | `terraform -version` (expect ≥ 1.7.0) |
| kubectl | `brew install kubectl` | `sudo az aks install-cli` | `kubectl version --client` |
| Helm | `brew install helm` | `curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 \| bash` | `helm version` |
| Git | `brew install git` | `sudo apt-get install -y git` | `git --version` |
| Docker | [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/) | `sudo apt-get install -y docker.io` | `docker --version` |

### Accounts required

- **Azure account** with an active subscription — [create a free account](https://azure.microsoft.com/en-us/free/)
- **GitHub account** with this repository forked or cloned
- **OpenAI API key** OR **Azure OpenAI access**
  > Azure OpenAI requires an application and approval — allow 1–3 business days.
  > See [Azure OpenAI request form](https://aka.ms/oaiapply).
- **Email address for Let’s Encrypt** — a real, monitored inbox is required.
  > cert-manager registers it with Let’s Encrypt when issuing your TLS certificate.
  > You will receive expiry warning emails at 60 and 14 days before the 90-day expiry.
  > The certificate renews automatically; the emails are informational only.

---

## Step 1 — Gather your Azure information

### Values you need to collect

| Value | What it is | How to find it | Used in |
|---|---|---|---|
| Subscription ID | Billing account identifier | `az account show --query id -o tsv` | Terraform, GitHub Secrets |
| Tenant ID | Azure AD directory identifier | `az account show --query tenantId -o tsv` | GitHub Secrets |
| Your object ID | Your user identity in Azure AD | `az ad signed-in-user show --query id -o tsv` | Terraform Key Vault admin |
| Location | Azure region to deploy to | `az account list-locations -o table` | Terraform variables |

### Choosing a region

Pick the region closest to your users. All resources are deployed in this single region.

| Region name | Display name | Notes |
|---|---|---|
| `uksouth` | UK South | Recommended for UK users |
| `eastus` | East US | Largest region, most services available |
| `westeurope` | West Europe | Recommended for EU users |
| `australiaeast` | Australia East | Recommended for APAC users |
| `southeastasia` | Southeast Asia | Recommended for SE Asia users |

---

## Step 2 — Run the bootstrap script

### What it does

The script creates these Azure resources automatically:

- **Resource group** `rg-<project>-tfstate` — container for Terraform state storage
- **Storage account** `st<project>tfstate` — holds the Terraform state file
- **Blob container** `tfstate` — Terraform remote backend container
- **Service principal** `sp-<project>-github` — used by GitHub Actions to authenticate to Azure

It also creates two local files:

- `.deployment-config` — all the configuration values you will need later (gitignored)
- `.github-actions-credentials.json` — credentials JSON for GitHub Actions (gitignored)

### Run it

Open a terminal in the repository root and run:

```bash
chmod +x scripts/azure-bootstrap.sh
./scripts/azure-bootstrap.sh
```

The script will prompt you for:

- **Subscription ID** — your Azure subscription UUID
- **Location** — Azure region (default: `uksouth`)
- **Project name** — short name used in all resource names (default: `aiarchitect`, max 12 lowercase alphanumeric chars)
- **Environment** — `dev` or `prod` (default: `dev`)
- **OpenAI API key** — optional, press Enter to skip and set later

### What the output looks like

```text
══ Step 10 — Summary ══

╔══════════════════════════════════════════════════════════════╗
║              Bootstrap completed successfully!               ║
╚══════════════════════════════════════════════════════════════╝

Resources created:
  • Resource group:    rg-aiarchitect-tfstate
  • Storage account:   staiarchitecttfstate
  • Blob container:    tfstate
  • Service principal: sp-aiarchitect-github

Local files created:
  • .deployment-config
  • .github-actions-credentials.json

══ GitHub Secrets to add ══

Secret: AZURE_CREDENTIALS
Value:  (full contents of .github-actions-credentials.json)
        cat .github-actions-credentials.json

Secret: AZURE_SUBSCRIPTION_ID
Value:  xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

Secret: AZURE_TENANT_ID
Value:  xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

...and more. Keep this terminal output open while adding secrets.

Next step:
  1. Copy the variable example file:
       cp terraform/environments/dev.tfvars.example terraform/environments/dev.tfvars
  2. Fill in your values in dev.tfvars
  3. Run Terraform: cd terraform && terraform init ...
```

> **Keep this terminal window open.** You will copy the secret values into GitHub in Step 6.

---

## Step 3 — Configure Terraform variables

### Copy the example file

```bash
cp terraform/environments/dev.tfvars.example \
   terraform/environments/dev.tfvars
```

### Fill in the required values

> `dev.tfvars` is in `.gitignore` — never commit it.

| Variable | Required | Where to get the value |
|---|---|---|
| `subscription_id` | Yes | `az account show --query id -o tsv` |
| `location` | No (default: `uksouth`) | `az account list-locations -o table` |
| `environment` | No (default: `dev`) | `dev` or `prod` |
| `project` | No (default: `aiarchitect`) | Lowercase alphanumeric, max 12 chars |
| `deployer_object_id` | Yes | `az ad signed-in-user show --query id -o tsv` |
| `aks_node_count` | No (default: `2`) | Number of initial AKS nodes |
| `aks_min_node_count` | No (default: `1`) | Auto-scaling lower bound |
| `aks_max_node_count` | No (default: `5`) | Auto-scaling upper bound (cost cap) |
| `aks_node_vm_size` | No (default: `Standard_D2s_v3`) | VM size for AKS nodes |
| `db_admin_username` | No (default: `aiarchitect`) | PostgreSQL admin login |
| `db_sku` | No (default: `B_Standard_B1ms`) | PostgreSQL SKU tier |
| `db_storage_mb` | No (default: `32768`) | Database storage in MB |
| `llm_provider` | No (default: `openai`) | `openai` or `azure` |
| `github_actions_sp_object_id` | No | `az ad sp list --display-name sp-aiarchitect-github --query '[0].id' -o tsv` |
| `openai_api_key` | Conditional | Use env var — do not put in `.tfvars` |
| `azure_openai_endpoint` | Conditional | Use env var — do not put in `.tfvars` |
| `azure_openai_api_key` | Conditional | Use env var — do not put in `.tfvars` |

### Handle sensitive values with environment variables

API keys must not go in `.tfvars` files. Terraform reads `TF_VAR_`-prefixed
environment variables automatically, so export them before running Terraform:

```bash
# For OpenAI:
export TF_VAR_openai_api_key="sk-your-key-here"

# Or for Azure OpenAI:
export TF_VAR_azure_openai_endpoint="https://your-resource.openai.azure.com/"
export TF_VAR_azure_openai_api_key="your-key-here"
export TF_VAR_llm_provider="azure"
```

---

## Step 4 — Run Terraform

### What will be created

```text
Azure Resource Group: rg-aiarchitect-dev
|
+-- Azure Container Registry
|     Stores your Docker images
|
+-- AKS Cluster
|     +-- System node pool  (API + UI pods, D2s_v3)
|     +-- Agent node pool   (Python agent pods, D4s_v3, tainted)
|
+-- PostgreSQL Flexible Server
|     Database: aiarchitect
|
+-- Key Vault
      Stores: db password, JWT secret, OpenAI key, internal secret
```

### Approximate monthly cost

| Resource | Dev (B/D2-series) | Prod (D4-series) |
|---|---|---|
| AKS nodes (2× D2s_v3 system + 1× D4s_v3 agent) | ~$140/month | ~$280/month |
| PostgreSQL B_Standard_B1ms | ~$15/month | ~$75/month (GP_Standard_D2s_v3) |
| Container Registry Basic | ~$5/month | ~$5/month |
| Load Balancer | ~$20/month | ~$20/month |
| Log Analytics + monitoring | ~$5/month | ~$10/month |
| **Total estimate** | **~$185/month** | **~$390/month** |

> Estimates are approximate and vary by usage. Tear down dev when not in use:
> `terraform destroy -var-file=environments/dev.tfvars`

### Run Terraform

```bash
cd terraform

terraform init \
  -backend-config="resource_group_name=rg-aiarchitect-tfstate" \
  -backend-config="storage_account_name=staiarchitecttfstate" \
  -backend-config="container_name=tfstate" \
  -backend-config="key=aiarchitect.tfstate"

terraform plan -var-file=environments/dev.tfvars

# Review the plan output. Every + means a resource will be created.
# When ready:
terraform apply -var-file=environments/dev.tfvars
# Type yes when prompted. Takes 10-15 minutes.
```

> Replace the backend config values with those printed by the bootstrap script,
> or source `.deployment-config` first to have them available as environment variables.

### Reading the output

After apply completes, Terraform prints output values. Copy them — you need
them for GitHub Secrets in Step 6.

| Output name | Used for |
|---|---|
| `resource_group_name` | `AZURE_RESOURCE_GROUP` secret |
| `acr_login_server` | `ACR_LOGIN_SERVER` secret; Docker image references |
| `acr_name` | `ACR_NAME` secret |
| `aks_cluster_name` | `AKS_CLUSTER_NAME` secret; `kubectl` context |
| `key_vault_name` | `KEY_VAULT_NAME` secret; Helm chart values |
| `key_vault_tenant_id` | `KEY_VAULT_TENANT_ID` secret |
| `aks_kubelet_client_id` | `AKS_KUBELET_CLIENT_ID` secret; Key Vault CSI auth |
| `db_fqdn` | Reference only — stored in Key Vault via connection string |
| `get_credentials_command` | Configure kubectl: copy and run this command |
| `github_secrets_summary` | Pre-formatted block of all remaining secret values |
| `ingress_ip` | Static public IP — point a DNS A record here for a custom domain |
| `ingress_fqdn` | Azure-assigned FQDN — use this if you have no custom domain |
| `https_url` | Ready-to-use HTTPS URL after cert-manager issues the certificate |

```bash
# Print all outputs at any time:
terraform output

# Print the pre-formatted GitHub Secrets block:
terraform output github_secrets_summary
```

---

## Step 5 — Run the post-Terraform setup script

### What it installs

- **nginx Ingress Controller** — routes external HTTP/HTTPS traffic into AKS
- **cert-manager** — automates TLS certificate provisioning (Let's Encrypt)
- **Azure Key Vault CSI driver** — mounts Key Vault secrets as pod volumes
- **`ai-architect` namespace** — Kubernetes namespace for the application

### Run it

```bash
cd ..   # back to repo root
chmod +x scripts/post-terraform.sh
./scripts/post-terraform.sh
```

### Your application IP address

When the script finishes it prints the static IP address and Azure-assigned FQDN
for the nginx Ingress Controller's Azure Load Balancer. This is your entry point.

**If you have a domain:** create an A record pointing to the `ingress_ip` output:

```text
Host: aiarchitect  (or @)  →  IP: <printed IP>
```

**If you do not have a domain:** use the Azure-assigned FQDN that Terraform creates
automatically (printed by the script as `ingress_fqdn`):

```text
https://<project>-<environment>.<region>.cloudapp.azure.com
Example: https://aiarchitect-dev.uksouth.cloudapp.azure.com
```

---

## Step 5b — HTTPS and TLS certificates

### Why HTTPS is required

Without HTTPS, browsers display a “Not Secure” warning and require users to click
through an Advanced option before they can access the application. All traffic
— including JWT tokens and architecture data — is transmitted in plaintext.

This deployment uses [cert-manager](https://cert-manager.io/) with Let’s Encrypt
to issue a fully browser-trusted certificate automatically. No manual certificate
management is required; cert-manager renews certificates 30 days before the
90-day expiry.

### Two-phase approach: staging then production

Let’s Encrypt imposes a **rate limit of 5 duplicate certificates per domain per week**
on its production issuer. Exhausting this limit during debugging means waiting 7 days
before a new certificate can be issued.

The deployment uses a **staging issuer first**:

| Phase | Issuer | CA trusted by browsers? | Rate limit |
|-------|--------|------------------------|------------|
| 1 — Verify setup | `letsencrypt-staging` | No (staging CA) | Very high |
| 2 — Go live | `letsencrypt-prod` | Yes | 5/week |

The staging certificate allows you to verify the ACME HTTP-01 challenge works
correctly without consuming production quota. Once the staging certificate shows
`READY = True`, run `scripts/switch-to-prod-tls.sh` to upgrade to the production issuer.

### Checking certificate status

```bash
# Check certificate status
kubectl get certificate -n ai-architect

# Detailed status with events
kubectl describe certificate ai-architect-tls -n ai-architect

# Check the ACME challenge
kubectl get challenges -n ai-architect

# cert-manager logs for debugging
kubectl logs -n cert-manager \
  -l app.kubernetes.io/name=cert-manager \
  --tail=50
```

### Switching from staging to production

Once the staging certificate shows `READY = True`:

```bash
./scripts/switch-to-prod-tls.sh
```

The script requires explicit confirmation before proceeding, upgrades the Helm
release to use `letsencrypt-prod`, deletes the staging certificate to trigger
re-issuance, and polls until the production certificate is `READY`.

### Troubleshooting failed certificate issuance

| Symptom | Cause | Fix |
|---------|-------|-----|
| Challenge fails with `connection refused` | Port 80 is not open or nginx is not running | Verify nginx ingress is running and the static IP is assigned: `kubectl get svc -n ingress-nginx` |
| `Rate limit exceeded` | Production issuer used too many times during debugging | Use staging issuer first; switch to production only once staging certificate is verified READY |
| Certificate stays in `Pending` | DNS not propagated or IP not reachable | Verify the ingress host resolves to the correct IP: `nslookup <host>` |
| `Wrong ingress class` | cert-manager cannot find the right ingress | Verify the ingress class annotation matches `nginx`: `kubectl describe ingress -n ai-architect` |

### Custom domain vs Azure-assigned FQDN

**No custom domain (recommended for dev):** Use the Azure-assigned FQDN printed by
the post-terraform script. No DNS setup required — the name resolves immediately.

**Custom domain:** Set the `INGRESS_HOSTNAME` GitHub Secret to your domain, then
create a DNS `A` record pointing to `ingress_ip` after `terraform apply`:

```text
Host: aiarchitect  (or @)  →  IP: <terraform output ingress_ip>
```

DNS propagation takes 1–60 minutes depending on your DNS provider. cert-manager
cannot issue a certificate until the host resolves publicly.

---

## Step 6 — Configure GitHub

### Create deployment environments

1. Go to your GitHub repository
2. Click **Settings** → **Environments**
3. Click **New environment** and name it `production`
4. Optionally add required reviewers for deployment approval
5. Repeat — create a second environment named `terraform`

### Add repository secrets

Go to **Settings** → **Secrets and variables** → **Actions** → **New repository secret**.

Create every secret in this table:

| Secret name | Value | Where to find it |
|---|---|---|
| `AZURE_CREDENTIALS` | Full JSON blob | Contents of `.github-actions-credentials.json` — run `cat .github-actions-credentials.json` |
| `AZURE_SUBSCRIPTION_ID` | UUID | `az account show --query id -o tsv` |
| `AZURE_TENANT_ID` | UUID | `az account show --query tenantId -o tsv` |
| `AZURE_RESOURCE_GROUP` | `rg-aiarchitect-dev` | `terraform output resource_group_name` |
| `ACR_LOGIN_SERVER` | `acr....azurecr.io` | `terraform output acr_login_server` |
| `ACR_NAME` | `acr...` | `terraform output acr_name` |
| `AKS_CLUSTER_NAME` | `aks-...` | `terraform output aks_cluster_name` |
| `KEY_VAULT_NAME` | `kv-...` | `terraform output key_vault_name` |
| `KEY_VAULT_TENANT_ID` | UUID | `terraform output key_vault_tenant_id` |
| `AKS_KUBELET_CLIENT_ID` | UUID | `terraform output aks_kubelet_client_id` |
| `TF_BACKEND_RESOURCE_GROUP` | `rg-aiarchitect-tfstate` | Bootstrap script output |
| `TF_BACKEND_STORAGE_ACCOUNT` | `staiarchitecttfstate` | Bootstrap script output |
| `TF_VAR_SUBSCRIPTION_ID` | UUID | `az account show --query id -o tsv` |
| `TF_VAR_DEPLOYER_OBJECT_ID` | UUID | `az ad signed-in-user show --query id -o tsv` |
| `TF_VAR_OPENAI_API_KEY` | `sk-...` | Your [OpenAI dashboard](https://platform.openai.com/api-keys) |
| `LETSENCRYPT_EMAIL` | `you@example.com` | Email for Let’s Encrypt. Receives expiry warnings. Required for cert issuance. |
| `TLS_ISSUER` | `letsencrypt-staging` | `letsencrypt-staging` or `letsencrypt-prod`. Default: staging. Change to prod after running `switch-to-prod-tls.sh`. |
| `INGRESS_HOSTNAME` | `archon.yourdomain.com` | Optional custom domain. Leave empty to use the Azure-assigned FQDN automatically. |
| `PROJECT_NAME` | `aiarchitect` | Project name matching the `project` Terraform variable. Used to construct the public IP resource name. |
| `ENVIRONMENT` | `dev` | Environment name matching the `environment` Terraform variable. Used to construct the public IP resource name. |

> **Tip:** the bootstrap script prints all of these values at the end in a formatted block.
> Keep that terminal output open while adding secrets to avoid switching between windows.

---

## Step 7 — First deployment

### Push to trigger the pipeline

```bash
git add .
git commit -m "Add deployment configuration"
git push origin main
```

### Watch the pipeline

1. Go to **GitHub** → **Actions**
2. Two workflows start: **CI** and **Deploy**
3. CI must pass before Deploy begins
4. In **Deploy**: `build-and-push` takes 5–10 minutes (first build; subsequent builds use layer cache)
5. In **Deploy**: `deploy` takes 3–5 minutes
6. Green tick on both means your application is live

### Verify it worked

```bash
kubectl get pods -n ai-architect
```

Expected output:

```text
NAME                                  READY   STATUS    RESTARTS
ai-architect-api-7d9f8b-xxxx         1/1     Running   0
ai-architect-agent-6c4d9a-xxxx       1/1     Running   0
ai-architect-ui-5b8e7f-xxxx          1/1     Running   0
```

### Open your application

Navigate to your HTTPS URL (use `terraform output https_url` to see it). You should
see the AI Architect Assistant interface. HTTP requests are automatically redirected
to HTTPS by the nginx `ssl-redirect` annotation.

---

## Ongoing operations

### Deploy a code change

Push to `main`. The pipeline runs automatically. Nothing else to do.

### Make infrastructure changes

Edit files in `terraform/` and push. The Terraform workflow shows a plan as a
PR comment when you open a pull request. Merge to `main` to apply the changes.

### View application logs

```bash
# API logs
kubectl logs -l app=ai-architect-api -n ai-architect --tail=100 -f

# Agent logs
kubectl logs -l app=ai-architect-agent -n ai-architect --tail=100 -f

# All pods
kubectl get pods -n ai-architect
```

### Check circuit breaker status

```bash
curl https://your-domain/api/actuator/circuitbreakers
```

### View token usage for a session

```bash
curl https://your-domain/api/v1/sessions/CONVERSATION_ID/usage \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### View architecture tactics for a session

The `tactics_recommendation` stage (stage 4b) runs after characteristics are
inferred and before conflict analysis. It recommends architecture tactics from
the Bass, Clements, and Kazman catalog ("Software Architecture in Practice",
4th ed.) for each quality attribute identified in the design.

```bash
# All tactics for a session
curl https://your-domain/api/v1/sessions/CONVERSATION_ID/tactics \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Only critical, unaddressed tactics (useful for a quick risk summary)
curl "https://your-domain/api/v1/sessions/CONVERSATION_ID/tactics?priority=critical&newOnly=true" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Tactics for a specific quality characteristic (e.g. availability)
curl "https://your-domain/api/v1/sessions/CONVERSATION_ID/tactics?characteristic=availability" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Aggregated summary (counts + top critical tactics)
curl https://your-domain/api/v1/sessions/CONVERSATION_ID/tactics/summary \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Query parameters** for the tactics endpoint:

| Parameter | Values | Description |
|-----------|--------|-------------|
| `characteristic` | any string | Filter by quality characteristic name (case-insensitive prefix match) |
| `priority` | `critical`, `recommended`, `optional` | Filter by tactic priority |
| `newOnly` | `true` | Exclude tactics the LLM flagged as already addressed in the design |

### Scale for production

Edit `terraform/environments/prod.tfvars` with larger VM sizes and node counts, then:

```bash
cd terraform
terraform apply -var-file=environments/prod.tfvars
```

### Tear down to save cost

```bash
cd terraform
terraform destroy -var-file=environments/dev.tfvars
```

> **Warning:** this permanently deletes the PostgreSQL database and all stored
> conversations. The Key Vault enters soft-delete for 7 days (recoverable).
> Back up your data first if needed.

---

## Architecture overview

```text
Internet
    |
    v
Azure Load Balancer (static public IP — pip-<project>-<env>-ingress)
    |
    v
nginx Ingress Controller (AKS — namespace: ingress-nginx)
  TLS terminated here — cert-manager / Let's Encrypt certificate
  HTTP → HTTPS redirect is enforced by ssl-redirect annotation
    |
    +-- /     --> UI pods      (nginx, React SPA)
    |
    +-- /api  --> API pods     (Spring Boot)
                      |
                      v
                 Agent pods   (FastAPI + LangGraph — agent node pool)
                      |
               +------+------+
               |             |
               v             v
          Qdrant         OpenAI API
      (vector memory)   (external)
               |
               v
         PostgreSQL     Key Vault
        (Azure managed) (secrets via CSI driver)
```

### Pipeline stages

Each architecture analysis runs 13 sequential stages. The UI progress bar
tracks them in order. Stages emit `STAGE_START` and `STAGE_COMPLETE` events
via SSE.

| # | Stage name | Description |
|---|-----------|-------------|
| 1 | `requirement_parsing` | Parse and structure the submitted requirements |
| 2 | `challenge_identification` | Identify key architectural challenges |
| 3 | `scenario_modeling` | Model quality attribute scenarios |
| 4 | `characteristic_inference` | Infer architecture characteristics from requirements |
| 4b | `tactics_recommendation` | Recommend architecture tactics (Bass/Clements/Kazman catalog) |
| 5 | `conflict_analysis` | Detect conflicts between characteristics |
| 6 | `architecture_generation` | Generate candidate architecture styles |
| 7 | `diagram_generation` | Generate C4 architecture diagram |
| 8 | `trade_off_analysis` | Analyse trade-offs between candidate styles |
| 9 | `adl_generation` | Generate Architecture Definition Language (ADL) rules |
| 10 | `weakness_analysis` | Identify architectural weaknesses |
| 11 | `fmea_analysis` | Failure Mode and Effects Analysis |
| 12 | `architecture_review` | Final review and scoring (with optional reiteration) |

---

## Troubleshooting

### Pod problems

| Symptom | Most likely cause | Fix |
|---|---|---|
| `ImagePullBackOff` | AcrPull role not assigned to kubelet identity | Re-run `scripts/azure-bootstrap.sh` then `terraform apply` |
| `CrashLoopBackOff` | Application startup error (missing env var, bad secret) | `kubectl logs <pod-name> -n ai-architect` |
| `Pending` | Insufficient node capacity or taint mismatch | `kubectl describe pod <pod-name> -n ai-architect` and check Events |
| Init container failing | Key Vault CSI could not mount secrets | Re-run `scripts/post-terraform.sh` then `kubectl rollout restart deployment -n ai-architect` |
| Agent pods `Pending` | No nodes in agent pool matching taint tolerance | Check node pool exists: `kubectl get nodes --show-labels` |

### Terraform problems

| Error message | Cause | Fix |
|---|---|---|
| `Error acquiring the state lock` | Interrupted apply left stale lock | `terraform force-unlock <lock-id>` — copy the lock ID from the error |
| `A resource with the ID already exists` | Name collision with prior deployment | Change the `project` variable in `.tfvars` |
| `AuthorizationFailed` | Not logged in or wrong active subscription | `az login` then `az account set --subscription <id>` |
| `QuotaExceeded` | Subscription VM quota limit | Use smaller `aks_node_vm_size` in `.tfvars` or request quota increase |
| `Key Vault name already exists in soft-deleted state` | Prior KV with same name in soft-delete | `az keyvault recover --name kv-<project>-<env>` |

### GitHub Actions problems

| Failure | Cause | Fix |
|---|---|---|
| `azure/login` fails | Invalid `AZURE_CREDENTIALS` secret | Regenerate service principal: re-run `scripts/azure-bootstrap.sh`, update secret |
| Push to ACR fails | Missing AcrPush role on service principal | `az role assignment create --assignee <sp-object-id> --role AcrPush --scope <acr-resource-id>` |
| Helm deploy fails | Pods not starting — check debug step | Expand the **Debug failed pods** step in the deploy job for logs and events |
| `terraform fmt` fails | Formatting issue in a `.tf` file | Run `terraform fmt -recursive` in `terraform/` locally, commit the result |
| Coverage below 80% | Missing tests for new code | Add tests before pushing; check coverage report in the artifact |
| `fromJson(secrets.AZURE_CREDENTIALS)` error | Secret not set or malformed JSON | Verify the secret contains valid JSON — `cat .github-actions-credentials.json | python3 -m json.tool` |

---

## Security notes

- **Secrets live in Azure Key Vault and GitHub Secrets only** — never in code or git commits
- **AKS uses managed identities** — no passwords are needed for Azure service-to-service access
- **Network policies** restrict which pods can communicate with which services within the cluster
- **PostgreSQL requires TLS** — `sslmode=require` is enforced in the connection string
- **JWT tokens** are stored in Zustand memory only — never in `localStorage` or cookies
- **Rate limiting** is active — 20 requests per minute per authenticated user
- `.github-actions-credentials.json` is in `.gitignore` — verify with `git status` before committing
- `.deployment-config` is in `.gitignore` — contains subscription IDs and object IDs
