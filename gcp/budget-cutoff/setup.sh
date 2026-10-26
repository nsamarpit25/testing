#!/bin/bash
# Billing cutoff: both budgets publish to a Pub/Sub topic; the function in main.py
# unlinks billing from every project once a budget's actual spend reaches its amount.
# Safe to re-run.
set -euo pipefail
cd "$(dirname "$0")"

ACCOUNT=0167C4-379354-1D8D7B
PROJECT=project-bebe18d3-83f6-445f-bdd
REGION=asia-south1
TOPIC=budget-cutoff
SA=budget-cutoff@$PROJECT.iam.gserviceaccount.com

echo "== Enabling APIs"
gcloud services enable pubsub.googleapis.com cloudfunctions.googleapis.com run.googleapis.com \
  cloudbuild.googleapis.com artifactregistry.googleapis.com eventarc.googleapis.com \
  cloudbilling.googleapis.com --project=$PROJECT

echo "== Topic"
gcloud pubsub topics describe $TOPIC --project=$PROJECT >/dev/null 2>&1 \
  || gcloud pubsub topics create $TOPIC --project=$PROJECT
gcloud pubsub topics add-iam-policy-binding $TOPIC --project=$PROJECT \
  --member=serviceAccount:billing-budget-alert@system.gserviceaccount.com \
  --role=roles/pubsub.publisher >/dev/null

echo "== Service account"
gcloud iam service-accounts describe $SA --project=$PROJECT >/dev/null 2>&1 \
  || gcloud iam service-accounts create budget-cutoff --display-name="Budget cutoff" --project=$PROJECT
gcloud billing accounts add-iam-policy-binding $ACCOUNT \
  --member=serviceAccount:$SA --role=roles/billing.admin >/dev/null
for p in $(gcloud billing projects list --billing-account=$ACCOUNT --format='value(projectId)'); do
  echo "   billing manager on $p"
  gcloud projects add-iam-policy-binding $p --member=serviceAccount:$SA \
    --role=roles/billing.projectManager --condition=None >/dev/null
done
gcloud projects add-iam-policy-binding $PROJECT --member=serviceAccount:$SA \
  --role=roles/run.invoker --condition=None >/dev/null
# New projects' default build account has no build rights, so build as $SA.
gcloud projects add-iam-policy-binding $PROJECT --member=serviceAccount:$SA \
  --role=roles/cloudbuild.builds.builder --condition=None >/dev/null

echo "== Function"
# The first deploy's own repo creation times out; create it ahead (takes ~2 min).
gcloud artifacts repositories describe gcf-artifacts --location=$REGION --project=$PROJECT >/dev/null 2>&1 \
  || gcloud artifacts repositories create gcf-artifacts --repository-format=docker \
       --location=$REGION --project=$PROJECT
gcloud functions deploy budget-cutoff --gen2 --region=$REGION --project=$PROJECT \
  --runtime=python312 --source=. --entry-point=stop_billing --trigger-topic=$TOPIC \
  --service-account=$SA --trigger-service-account=$SA \
  --build-service-account=projects/$PROJECT/serviceAccounts/$SA --max-instances=1 --quiet

echo "== Connecting budgets"
for b in $(gcloud billing budgets list --billing-account=$ACCOUNT --billing-project=$PROJECT \
    --format='value(name.basename())'); do
  gcloud billing budgets update $b --billing-account=$ACCOUNT --billing-project=$PROJECT \
    --notifications-rule-pubsub-topic=projects/$PROJECT/topics/$TOPIC
done

echo "== Done"
