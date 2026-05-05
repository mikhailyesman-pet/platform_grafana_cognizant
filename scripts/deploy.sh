#!/bin/bash

# Deploy Grafana Infrastructure using CloudFormation
# Usage: ./deploy.sh [dev|uat|prod]

set -e

ENVIRONMENT="${1:-dev}"
REGION="${AWS_REGION:-us-east-1}"
STACK_NAME="grafana-observability-${ENVIRONMENT}"
TEMPLATE_FILE="templates/01-main-stack.yaml"
PARAMETERS_FILE="parameters/${ENVIRONMENT}-parameters.json"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Deploying Grafana Infrastructure${NC}"
echo "Environment: $ENVIRONMENT"
echo "Region: $REGION"
echo "Stack: $STACK_NAME"
echo "Template: $TEMPLATE_FILE"
echo "Parameters: $PARAMETERS_FILE"
echo ""

# Validate parameters
if [ ! -f "$PARAMETERS_FILE" ]; then
    echo -e "${RED}Error: Parameters file not found: $PARAMETERS_FILE${NC}"
    exit 1
fi

if [ ! -f "$TEMPLATE_FILE" ]; then
    echo -e "${RED}Error: Template file not found: $TEMPLATE_FILE${NC}"
    exit 1
fi

# Validate CloudFormation template
echo -e "${YELLOW}Validating CloudFormation template...${NC}"
aws cloudformation validate-template \
    --template-body file://$TEMPLATE_FILE \
    --region $REGION > /dev/null

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Template validation passed${NC}"
else
    echo -e "${RED}✗ Template validation failed${NC}"
    exit 1
fi

# Check if stack exists
echo -e "${YELLOW}Checking if stack already exists...${NC}"
STACK_EXISTS=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region $REGION \
    --query 'Stacks[0].StackId' \
    --output text 2>/dev/null || echo "")

if [ -n "$STACK_EXISTS" ]; then
    echo -e "${YELLOW}Stack exists. Updating...${NC}"
    OPERATION="update-stack"
    WAIT_CONDITION="stack-update-complete"
else
    echo -e "${YELLOW}Stack does not exist. Creating...${NC}"
    OPERATION="create-stack"
    WAIT_CONDITION="stack-create-complete"
fi

# Deploy/Update stack
echo -e "${YELLOW}Deploying stack...${NC}"
aws cloudformation $OPERATION \
    --stack-name "$STACK_NAME" \
    --template-body file://$TEMPLATE_FILE \
    --parameters file://$PARAMETERS_FILE \
    --capabilities CAPABILITY_NAMED_IAM \
    --region $REGION

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Stack deployment failed${NC}"
    exit 1
fi

# Wait for stack operation to complete
echo -e "${YELLOW}Waiting for stack operation to complete...${NC}"
aws cloudformation wait $WAIT_CONDITION \
    --stack-name "$STACK_NAME" \
    --region $REGION

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Stack deployment completed successfully${NC}"
else
    echo -e "${RED}✗ Stack deployment failed${NC}"
    exit 1
fi

# Get stack outputs
echo -e "${YELLOW}Stack outputs:${NC}"
aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region $REGION \
    --query 'Stacks[0].Outputs' \
    --output table

echo -e "${GREEN}Deployment completed! ✓${NC}"
