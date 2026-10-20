---
name: cloud-basics
description: Plain, basic guide to using Google Cloud (GCP/Vertex) and AWS from this Mac - check you're logged in, check credits, see what's running, stop things. Use when the user asks how to use GCP/GCS/AWS, whether credentials work, or how many credits are left.
---

# Cloud basics (Google Cloud + AWS)

Keep it simple. Never print keys, tokens or the contents of `~/.aws/credentials`. Never type passwords for the user - they log in themselves.

## Google Cloud (GCP)

What it's for here: Gemini on Vertex AI (e.g. `scripts/ask_argon.py`). The CLI is `gcloud` (`/opt/homebrew/bin/gcloud`).

Two kinds of login:
- **CLI login** (for `gcloud` commands): `gcloud auth list` shows who's logged in. Log in with `gcloud auth login`.
- **App login / ADC** (what Python scripts use): check with
  `gcloud auth application-default print-access-token >/dev/null && echo ok`
  Log in with `gcloud auth application-default login`.

Project: `gcloud config get-value project` shows the default one. Set it with `gcloud config set project <id>`.

Credits: the CLI can't show them. Open https://console.cloud.google.com/billing → your billing account → **Credits**.

"GCS" strictly means Cloud Storage (buckets). Basic use: `gcloud storage ls`, `gcloud storage cp file gs://bucket/`.

## AWS

The CLI profile is `manmeet`. Add `--profile manmeet` to every command. Regions used: `us-east-1` (Virginia), `ap-south-1` (Mumbai).

Check credentials work:
```bash
aws sts get-caller-identity --profile manmeet
aws configure list --profile manmeet
```
If it errors, keys are missing/expired - the user runs `aws configure --profile manmeet` themselves.

Credits left:
```bash
aws freetier get-account-plan-state --profile manmeet --region us-east-1
```

Is anything running (costs money)? Run per region:
```bash
aws ec2 describe-instances --profile manmeet --region ap-south-1 --filters Name=instance-state-name,Values=pending,running --query "Reservations[].Instances[].[InstanceId,InstanceType]" --output text
```

Stop vs terminate:
- **Stop**: no compute charge, but the disk still costs a little (~$0.08/GB/month).
- **Terminate**: deletes it, no charges. Ask the user before terminating.

GPU quota (how many GPU vCPUs you may run; code `L-DB2E81BA` = G and VT instances):
```bash
aws service-quotas get-service-quota --profile manmeet --region us-east-1 --service-code ec2 --quota-code L-DB2E81BA --query Quota.Value
```

Payment method and bills: console only - https://console.aws.amazon.com/billing/home#/paymentpreferences

If `aws` says credentials not found: you forgot `--profile manmeet` (or `export AWS_PROFILE=manmeet`). That profile signs in with `aws login`; if its session expired, the user runs `aws login --profile manmeet`.

SSH into the render GPU: the key is `~/.ssh/ctv2-bench.pem` and the host entry is in `~/.ssh/ctv2_aws.conf`:
```bash
ssh -F ~/.ssh/ctv2_aws.conf ctv2-gpu
```
Its IP changes every launch. Find the new one and put it in that file's `HostName`:
```bash
aws ec2 describe-instances --profile manmeet --region us-east-1 --filters Name=instance-state-name,Values=running --query "Reservations[].Instances[].PublicIpAddress" --output text
```
