#!/bin/bash

# Deploy Grafana infrastructure using packaged nested CloudFormation templates.
# Usage: CFN_ARTIFACT_BUCKET=my-bucket GRAFANA_ADMIN_PASSWORD='...' ./deploy.sh

set -e

ENVIRONMENT="${1:-dev}"
REGION="${AWS_REGION:-us-east-1}"
STACK_NAME="grafana-observability-${ENVIRONMENT}"
TEMPLATE_FILE="templates/01-main-stack.yaml"
PACKAGED_TEMPLATE="packaged-template.yaml"
PARAMETERS_FILE="parameters/${ENVIRONMENT}-parameters.json"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

if [ -z "$CFN_ARTIFACT_BUCKET" ]; then
    echo -e "${RED}Error: CFN_ARTIFACT_BUCKET is required for nested stack packaging${NC}"
    exit 1
fi

if [ -z "$GRAFANA_ADMIN_PASSWORD" ]; then
    echo -e "${RED}Error: GRAFANA_ADMIN_PASSWORD must be provided from the shell or secret manager${NC}"
    exit 1
fi

if [ ! -f "$PARAMETERS_FILE" ]; then
    echo -e "${RED}Error: parameters file not found: $PARAMETERS_FILE${NC}"
    exit 1
fi

echo -e "${YELLOW}Packaging CloudFormation templates${NC}"
aws cloudformation package \
    --template-file "$TEMPLATE_FILE" \
    --s3-bucket "$CFN_ARTIFACT_BUCKET" \
    --output-template-file "$PACKAGED_TEMPLATE" \
    --region "$REGION"

PARAMETER_OVERRIDES=$(jq -r '.[] | "\(.ParameterKey)=\(.ParameterValue)"' "$PARAMETERS_FILE")

echo -e "${YELLOW}Deploying stack $STACK_NAME${NC}"
aws cloudformation deploy \
    --template-file "$PACKAGED_TEMPLATE" \
    --stack-name "$STACK_NAME" \
    --parameter-overrides $PARAMETER_OVERRIDES GrafanaAdminPassword="$GRAFANA_ADMIN_PASSWORD" \
    --capabilities CAPABILITY_NAMED_IAM \
    --region "$REGION" \
    --no-fail-on-empty-changeset

echo -e "${YELLOW}Stack outputs${NC}"
aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs' \
    --output table

echo -e "${GREEN}Deployment completed successfully${NC}"
