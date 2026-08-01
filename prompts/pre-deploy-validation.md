Before this deployment runs, validate:
1. All secrets referenced in helm/ai-architect/templates/
   exist in Key Vault kv-axiom-dev-bpxn
2. All database names referenced in POSTGRES_URL env vars
   exist on psql-axiom-dev-bpxn
3. All probe initialDelaySeconds are >= 90 for Spring Boot services
4. nginx.conf proxy_pass points to axiom-api:8080 not a pillar service
5. All --set flags in deploy.yml match values.yaml keys
Report any violations before the push proceeds.