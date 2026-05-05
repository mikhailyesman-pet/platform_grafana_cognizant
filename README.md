# AWS Managed Grafana Observability

Infrastructure as Code for a single-account AWS Managed Grafana and CloudWatch observability setup.

## What This Builds

- AWS Managed Grafana workspace with AWS IAM Identity Center authentication enabled.
- CloudWatch data source permissions through a customer-managed Grafana service role.
- Plugin management enabled and basic plugins installed by a CloudFormation custom resource.
- CloudWatch log groups, metric filters, alarms, and CloudWatch dashboards.
- One SNS topic and email subscription for Grafana and CloudWatch alert notifications.
- Grafana dashboards and unified alerting resources deployed automatically from GitHub Actions.

## Repository Layout

```text
templates/
  01-main-stack.yaml        Root nested-stack orchestration template
  02-grafana-stack.yaml     Managed Grafana workspace and custom resources
  03-cloudwatch-stack.yaml  CloudWatch logs, metrics, alarms, dashboards
  04-sns-stack.yaml         SNS topics, subscriptions, policies
  05-iam-roles.yaml         IAM roles for Grafana and Lambda
parameters/
  dev-parameters.json
dashboards/                 Grafana dashboard JSON files
alerts/                     Grafana alert rule definitions
scripts/                    Local deployment and API helper scripts
.github/workflows/deploy.yml
```

## Prerequisites

- AWS CLI configured for the target account.
- IAM permissions for CloudFormation, IAM, Grafana, Lambda, CloudWatch, SNS, SSM, and Secrets Manager.
- An S3 bucket for packaged nested CloudFormation templates.
- Confirmed SNS email subscriptions after deployment.
- A Grafana service account token or API key stored in GitHub secrets for dashboard and alert deployment.

## Deploy Locally

Package the nested templates before deploying the root stack:

```bash
aws cloudformation package \
  --template-file templates/01-main-stack.yaml \
  --s3-bucket <cloudformation-artifact-bucket> \
  --output-template-file packaged-template.yaml

PARAMETER_OVERRIDES=$(jq -r '.[] | "\(.ParameterKey)=\(.ParameterValue)"' parameters/dev-parameters.json)

aws cloudformation deploy \
  --template-file packaged-template.yaml \
  --stack-name grafana-observability-dev \
  --parameter-overrides $PARAMETER_OVERRIDES \
  --capabilities CAPABILITY_NAMED_IAM
```

Deploy dashboards and alerts after the stack is ready:

```bash
python scripts/deploy-dashboards.py \
  --grafana-url "$GRAFANA_URL" \
  --api-key "$GRAFANA_API_KEY" \
  --dashboards-dir dashboards/

python scripts/setup-alerts.py \
  --grafana-url "$GRAFANA_URL" \
  --api-key "$GRAFANA_API_KEY" \
  --alerts-dir alerts/ \
  --sns-topic-arn "$GRAFANA_ALERTS_SNS_TOPIC_ARN" \
  --region us-east-1 \
  --environment dev
```

## GitHub Actions

The workflow validates templates, packages nested stacks, deploys the selected environment, then deploys dashboards and alerts through the Grafana HTTP API.

Required repository or environment secrets:

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `CFN_ARTIFACT_BUCKET`
- `GRAFANA_ADMIN_PASSWORD`
- `GRAFANA_API_KEY`

The workflow deploys the single-account stack on pushes to `main` and can also be run manually.

## Validation

```bash
python3 -m py_compile scripts/*.py
for f in parameters/*.json alerts/*.json dashboards/*.json; do jq empty "$f"; done
cfn-lint -i W3002 -- templates/*.yaml
```

`W3002` is expected for local nested-stack template paths. The workflow packages those paths into S3 URLs before deployment.
