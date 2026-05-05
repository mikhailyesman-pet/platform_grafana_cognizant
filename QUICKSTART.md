# Quickstart

## 1. Update Parameters

Edit the target parameter file:

```bash
vi parameters/dev-parameters.json
```

Set a real `AlertEmail` and the desired `LogRetentionDays`. Do not store `GrafanaAdminPassword` in this file; pass it through `GRAFANA_ADMIN_PASSWORD` or GitHub Secrets.

## 2. Validate

```bash
python3 -m py_compile scripts/*.py
for f in parameters/*.json alerts/*.json dashboards/*.json; do jq empty "$f"; done
cfn-lint -i W3002 -- templates/*.yaml
```

## 3. Package and Deploy

```bash
aws cloudformation package \
  --template-file templates/01-main-stack.yaml \
  --s3-bucket <cloudformation-artifact-bucket> \
  --output-template-file packaged-template.yaml

PARAMETER_OVERRIDES=$(jq -r '.[] | "\(.ParameterKey)=\(.ParameterValue)"' parameters/dev-parameters.json)

aws cloudformation deploy \
  --template-file packaged-template.yaml \
  --stack-name grafana-observability-dev \
  --parameter-overrides $PARAMETER_OVERRIDES GrafanaAdminPassword="$GRAFANA_ADMIN_PASSWORD" \
  --capabilities CAPABILITY_NAMED_IAM
```

## 4. Get Outputs

```bash
aws cloudformation describe-stacks \
  --stack-name grafana-observability-dev \
  --query 'Stacks[0].Outputs' \
  --output table
```

## 5. Deploy Dashboards and Alerts

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

## 6. GitHub Actions

Add the required secrets from `README.md`, then push to `main` or run the workflow manually.
