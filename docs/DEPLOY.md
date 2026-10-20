# Deploying to Azure

The prototype runs as one container on Azure Container Apps. These are the steps that were
actually used, in order. Every resource is tagged `project=ttb-label-verifier`.

Live URL: https://ttb-label-verifier.kindmoss-39b6eae5.eastus2.azurecontainerapps.io

## What is deployed

| Resource | Name | Notes |
|---|---|---|
| Resource group | `rg-ttb-label-verifier` | East US 2, a region where Claude in Microsoft Foundry is offered |
| Container registry | `ttblabelverifier` | Basic tier, admin user off. Images are built in the cloud for linux/amd64. |
| Container Apps environment | `cae-ttb-label-verifier` | Consumption plan. **No log storage** (`--logs-destination none`). Live log streaming still works. |
| Container app | `ttb-label-verifier` | 2 vCPU, 4 GiB since Oct 20, 2026, for review week (1 vCPU, 2 GiB before): batches read the warning a second time with Tesseract, which needs the CPU. Scales 0 to 1 replica, public HTTPS. System-assigned managed identity pulls images from the registry. |
| Foundry resource | `ttb-foundry-cp` | Azure AI Foundry (AI Services), East US 2, for the optional Foundry reader. No Claude deployment yet (see below). |
| Budget | `ttb-label-verifier-monthly` | $40 a month for the subscription, email alerts at 50%, 80%, and 100%. Azure budgets alert; they do not stop spending. |

The app runs as **one replica at most**: usage limits and batch jobs are kept in memory, so a
second replica would not see them.

## One-time setup

```sh
az provider register -n Microsoft.App --wait
az provider register -n Microsoft.ContainerRegistry --wait
az extension add --name containerapp --upgrade

az group create -n rg-ttb-label-verifier -l eastus2 --tags project=ttb-label-verifier

az acr create -g rg-ttb-label-verifier -n ttblabelverifier --sku Basic -l eastus2 \
  --admin-enabled false --tags project=ttb-label-verifier

az containerapp env create -n cae-ttb-label-verifier -g rg-ttb-label-verifier -l eastus2 \
  --logs-destination none --tags project=ttb-label-verifier
```

## Build and deploy a version

Images are tagged with the git commit they were built from. Build from a clean working tree.
`.dockerignore` keeps `.env`, `private/`, tests, tools, and docs out of the upload. The sample
labels are included, for "Try a sample".

```sh
SHA=$(git rev-parse --short HEAD)
az acr build -r ttblabelverifier -t ttb-label-verifier:$SHA --platform linux/amd64 .
```

First deploy:

```sh
az containerapp create -n ttb-label-verifier -g rg-ttb-label-verifier \
  --environment cae-ttb-label-verifier \
  --image ttblabelverifier.azurecr.io/ttb-label-verifier:$SHA \
  --registry-server ttblabelverifier.azurecr.io --registry-identity system --system-assigned \
  --ingress external --target-port 8000 \
  --cpu 2.0 --memory 4.0Gi --min-replicas 0 --max-replicas 1 \
  --tags project=ttb-label-verifier
```

Later versions:

```sh
az containerapp update -n ttb-label-verifier -g rg-ttb-label-verifier \
  --image ttblabelverifier.azurecr.io/ttb-label-verifier:$SHA
```

## The Anthropic API key

The key is stored as a Container Apps secret and passed to the app as `ANTHROPIC_API_KEY`.
It never appears in code, the image, or this repository. Run this from the project folder;
it reads the key from your local `.env` without printing it:

```sh
set -a; . ./.env; set +a
az containerapp secret set -n ttb-label-verifier -g rg-ttb-label-verifier \
  --secrets anthropic-api-key="$ANTHROPIC_API_KEY" -o none
az containerapp update -n ttb-label-verifier -g rg-ttb-label-verifier \
  --set-env-vars ANTHROPIC_API_KEY=secretref:anthropic-api-key -o none
```

The key belongs to a dedicated Anthropic workspace with a monthly spend limit. That limit is
the hard stop on AI spending; the app also limits each visitor (each internet address) to 300
checks per 10 minutes and 30 batches per hour, and the whole app to 2,000 labels a day.

## Claude in Microsoft Foundry (optional, not yet validated)

For an agency whose firewall blocks outside AI services, the app can read labels with
Claude hosted in its own Azure subscription instead of the Anthropic API. The code is in
`app/reading/providers.py`. Requirements (Microsoft's, as of October 2026):

- **A paid subscription with a pay-as-you-go billing method.** Free trial, student, and
  credit-only subscriptions have no Claude quota.
- **A Foundry resource in a region that offers Claude** (East US 2 does), with a Claude Haiku 5.5
  deployment using the "Hosted on Azure" version, so prompts and answers stay in Azure.
- **The container app's managed identity** needs the "Cognitive Services User" role on the
  Foundry resource. Then no key is stored anywhere.
- **The default quota is low:** about 40 requests and 40,000 input tokens a minute for the whole
  subscription. Set `TTB_LABELS_PER_MINUTE` to stay inside it (a two-picture label uses
  about 7,000 input tokens), and lower `TTB_BATCH_CONCURRENCY`.

Then set `TTB_READER=foundry`, `TTB_FOUNDRY_RESOURCE=<resource name>`, and
`TTB_CLAUDE_MODEL=<deployment name>` on the container app. Foundry needs
`TTB_CLAUDE_THINKING=adaptive`, which is the default when `TTB_READER=foundry`.

**Status on Oct 19, 2026:**

- **Done:** the Foundry resource `ttb-foundry-cp` exists in `rg-ttb-label-verifier`, and the
  container app's identity has the "Cognitive Services User" role on it.
- **Keyless sign-in works.** A call to the real endpoint, signed in with Microsoft Entra ID, was
  accepted. It answered "deployment not found", not "unauthorized".
- **The Claude Haiku 5.5 deployment is not made yet, for two reasons:**
  - The subscription's quota for it is 0, so a quota request is needed.
  - Anthropic requires "model provider data" (industry, organization name, country) for every
    deployment.
- **So Foundry has been tested offline only** (`tests/reading/test_providers.py`), not on a live
  deployment.

```sh
az provider register -n Microsoft.CognitiveServices --wait
az cognitiveservices account create -n ttb-foundry-cp -g rg-ttb-label-verifier -l eastus2 \
  --kind AIServices --sku S0 --custom-domain ttb-foundry-cp --allow-project-management true \
  --tags project=ttb-label-verifier
az role assignment create --role "Cognitive Services User" \
  --assignee-object-id <container app principal id> --assignee-principal-type ServicePrincipal \
  --scope <Foundry resource id>
```

## Checking a deployment

```sh
curl -sS https://ttb-label-verifier.kindmoss-39b6eae5.eastus2.azurecontainerapps.io/health
az containerapp revision list -n ttb-label-verifier -g rg-ttb-label-verifier -o table
az containerapp logs show -n ttb-label-verifier -g rg-ttb-label-verifier --follow
```

The first request after the app has scaled to zero waits for a container to start: about 23
seconds, measured on Oct 19, 2026 (`docs/measurements/live-single-check-2026-10-19.md`).
Setting `--min-replicas 1` removes the wait, at the cost of a replica that never stops.

## Removing everything

```sh
az group delete -n rg-ttb-label-verifier
az consumption budget delete --budget-name ttb-label-verifier-monthly
```
