# Deployment Summary

This repository contains a single-account AWS Managed Grafana observability solution built with CloudFormation and GitHub Actions.

## Implemented Scope

- AWS Managed Grafana workspace with AWS IAM Identity Center authentication.
- Plugin management enabled, with plugin installation handled by a CloudFormation custom resource.
- CloudWatch log groups, metric filters, alarms, query definitions, and dashboards.
- One SNS alert topic, email subscription, and publish policy for CloudWatch and Grafana.
- Grafana dashboards stored as JSON and deployed through the Grafana HTTP API.
- Grafana unified alerting deployment with an SNS contact point, notification template, notification policy, and CloudWatch metric rules.
- GitHub Actions workflow for validation, CloudFormation packaging, infrastructure deployment, dashboards, and alerts.

## Important Operational Notes

- The root template uses nested stacks, so it must be packaged with `aws cloudformation package` before deployment.
- `CFN_ARTIFACT_BUCKET` must point to an S3 bucket in the target AWS account or a bucket that the deployment role can write to.
- Email subscriptions created by SNS must be confirmed by the recipient before notifications are delivered.
- Grafana dashboard and alert deployment requires a Grafana service account token or API key with admin-level permissions.
- AWS IAM Identity Center is enabled directly on the AWS Managed Grafana workspace.

## Validation Completed

```text
python3 -m py_compile scripts/*.py
jq validation for parameters, alerts, and dashboards
cfn-lint -i W3002 -- templates/*.yaml
```

`W3002` is intentionally ignored because local nested-stack paths are converted to S3 URLs during packaging.
