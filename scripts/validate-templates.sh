#!/bin/bash

# Validate CloudFormation templates
# Usage: ./validate-templates.sh

set -e

TEMPLATES_DIR="templates"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Validating CloudFormation templates...${NC}"
echo ""

FAILED=0
PASSED=0

# Check if cfn-lint is installed
if ! command -v cfn-lint &> /dev/null; then
    echo -e "${YELLOW}Installing cfn-lint...${NC}"
    pip install cfn-lint
fi

# Validate each template
for template in $TEMPLATES_DIR/*.yaml; do
    echo -e "${YELLOW}Validating $template...${NC}"
    
    # Run cfn-lint
    if cfn-lint "$template" -f pretty -i W; then
        echo -e "${GREEN}✓ $template is valid${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ $template has errors${NC}"
        ((FAILED++))
    fi
    echo ""
done

# Validate with AWS CLI if credentials are available
if aws sts get-caller-identity &> /dev/null; then
    echo -e "${YELLOW}Validating with AWS CloudFormation...${NC}"
    echo ""
    
    for template in $TEMPLATES_DIR/*.yaml; do
        echo -e "${YELLOW}Validating $template with AWS...${NC}"
        
        if aws cloudformation validate-template \
            --template-body file://$template \
            --query 'Description' \
            --output text > /dev/null; then
            echo -e "${GREEN}✓ AWS validation passed${NC}"
            ((PASSED++))
        else
            echo -e "${RED}✗ AWS validation failed${NC}"
            ((FAILED++))
        fi
        echo ""
    done
else
    echo -e "${YELLOW}AWS credentials not configured, skipping AWS validation${NC}"
fi

# Validate parameter files
echo -e "${YELLOW}Validating parameter files...${NC}"
echo ""

for params in parameters/*.json; do
    echo -e "${YELLOW}Checking $params...${NC}"
    
    if jq . "$params" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Valid JSON: $params${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ Invalid JSON: $params${NC}"
        ((FAILED++))
    fi
    echo ""
done

# Summary
echo -e "${YELLOW}Validation Summary:${NC}"
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All validations passed! ✓${NC}"
    exit 0
else
    echo -e "${RED}Some validations failed! ✗${NC}"
    exit 1
fi
