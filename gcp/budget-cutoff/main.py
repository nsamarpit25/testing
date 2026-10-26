"""Unlinks billing from every project on the account once a budget's spend reaches its amount.

Both budgets ("Usage (before credits)" and "Real money (after credits)") publish to the
budget-cutoff Pub/Sub topic several times a day; each message carries that budget's own
costAmount/budgetAmount, so one function serves both.

Re-enable afterwards with:
  gcloud billing projects link <project> --billing-account=0167C4-379354-1D8D7B
"""
import base64
import json

import functions_framework
from googleapiclient import discovery

BILLING_ACCOUNT = "billingAccounts/0167C4-379354-1D8D7B"
HOST_PROJECT = "project-bebe18d3-83f6-445f-bdd"  # runs this function, so it is cut last


@functions_framework.cloud_event
def stop_billing(cloud_event):
    data = json.loads(base64.b64decode(cloud_event.data["message"]["data"]))
    name = data.get("budgetDisplayName", "?")
    cost, budget = float(data["costAmount"]), float(data["budgetAmount"])

    billing = discovery.build("cloudbilling", "v1", cache_discovery=False)
    linked = billing.billingAccounts().projects().list(name=BILLING_ACCOUNT).execute()
    projects = [p["projectId"] for p in linked.get("projectBillingInfo", []) if p.get("billingEnabled")]
    print(f"{name}: {cost:.2f} / {budget:.2f} {data.get('currencyCode', '')}; billed projects: {projects}")

    if cost < budget:
        return

    projects.sort(key=lambda p: p == HOST_PROJECT)
    for project in projects:
        billing.projects().updateBillingInfo(
            name=f"projects/{project}", body={"billingAccountName": ""}
        ).execute()
        print(f"CUTOFF ({name}): billing disabled on {project}")
