#!/bin/bash

# Setup SSO for Grafana
# Usage: ./setup-sso.sh [dev|uat|prod] [SAML|OAUTH2_GOOGLE|OAUTH2_GITHUB|OAUTH2_AZURE]

set -e

ENVIRONMENT="${1:-dev}"
SSO_PROVIDER="${2:-SAML}"
REGION="${AWS_REGION:-us-east-1}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Setting up SSO for Grafana${NC}"
echo "Environment: $ENVIRONMENT"
echo "SSO Provider: $SSO_PROVIDER"
echo "Region: $REGION"
echo ""

# Get Grafana workspace ID from Parameter Store
WORKSPACE_ID=$(aws ssm get-parameter \
    --name "/grafana/workspace-id/${ENVIRONMENT}" \
    --query 'Parameter.Value' \
    --output text \
    --region $REGION 2>/dev/null || echo "")

if [ -z "$WORKSPACE_ID" ]; then
    echo -e "${RED}Error: Grafana workspace not found for environment: $ENVIRONMENT${NC}"
    exit 1
fi

echo -e "${YELLOW}Grafana Workspace ID: $WORKSPACE_ID${NC}"
echo ""

# Get Grafana URL
GRAFANA_ENDPOINT=$(aws ssm get-parameter \
    --name "/grafana/workspace-endpoint/${ENVIRONMENT}" \
    --query 'Parameter.Value' \
    --output text \
    --region $REGION)

echo -e "${YELLOW}Grafana URL: $GRAFANA_ENDPOINT${NC}"
echo ""

case $SSO_PROVIDER in
    SAML)
        echo -e "${YELLOW}Setting up SAML SSO...${NC}"
        echo "Please provide the following information:"
        read -p "SAML IdP Entry Point URL: " SAML_URL
        read -p "SAML Certificate (base64 encoded): " SAML_CERT
        read -p "SAML Email Attribute: " -i "email" SAML_EMAIL_ATTR
        
        # Store SAML configuration
        aws ssm put-parameter \
            --name "/grafana/sso/saml-url" \
            --value "$SAML_URL" \
            --type "String" \
            --overwrite \
            --region $REGION
        
        echo -e "${GREEN}✓ SAML configuration stored${NC}"
        ;;
        
    OAUTH2_GOOGLE)
        echo -e "${YELLOW}Setting up Google OAuth2...${NC}"
        echo "Please provide the following information:"
        read -p "Google OAuth2 Client ID: " GOOGLE_CLIENT_ID
        read -s -p "Google OAuth2 Client Secret: " GOOGLE_CLIENT_SECRET
        echo ""
        
        # Store Google OAuth2 configuration
        aws secretsmanager create-secret \
            --name "/grafana/sso/google-oauth2" \
            --secret-string "{\"client_id\":\"$GOOGLE_CLIENT_ID\",\"client_secret\":\"$GOOGLE_CLIENT_SECRET\"}" \
            --region $REGION 2>/dev/null || \
        aws secretsmanager update-secret \
            --secret-id "/grafana/sso/google-oauth2" \
            --secret-string "{\"client_id\":\"$GOOGLE_CLIENT_ID\",\"client_secret\":\"$GOOGLE_CLIENT_SECRET\"}" \
            --region $REGION
        
        echo -e "${GREEN}✓ Google OAuth2 configuration stored${NC}"
        ;;
        
    OAUTH2_GITHUB)
        echo -e "${YELLOW}Setting up GitHub OAuth2...${NC}"
        echo "Please provide the following information:"
        read -p "GitHub OAuth2 Client ID: " GITHUB_CLIENT_ID
        read -s -p "GitHub OAuth2 Client Secret: " GITHUB_CLIENT_SECRET
        echo ""
        
        # Store GitHub OAuth2 configuration
        aws secretsmanager create-secret \
            --name "/grafana/sso/github-oauth2" \
            --secret-string "{\"client_id\":\"$GITHUB_CLIENT_ID\",\"client_secret\":\"$GITHUB_CLIENT_SECRET\"}" \
            --region $REGION 2>/dev/null || \
        aws secretsmanager update-secret \
            --secret-id "/grafana/sso/github-oauth2" \
            --secret-string "{\"client_id\":\"$GITHUB_CLIENT_ID\",\"client_secret\":\"$GITHUB_CLIENT_SECRET\"}" \
            --region $REGION
        
        echo -e "${GREEN}✓ GitHub OAuth2 configuration stored${NC}"
        ;;
        
    OAUTH2_AZURE)
        echo -e "${YELLOW}Setting up Azure AD OAuth2...${NC}"
        echo "Please provide the following information:"
        read -p "Azure Tenant ID: " AZURE_TENANT_ID
        read -p "Azure Application (Client) ID: " AZURE_APP_ID
        read -s -p "Azure Client Secret: " AZURE_CLIENT_SECRET
        echo ""
        
        # Store Azure AD configuration
        aws secretsmanager create-secret \
            --name "/grafana/sso/azure-oauth2" \
            --secret-string "{\"tenant_id\":\"$AZURE_TENANT_ID\",\"client_id\":\"$AZURE_APP_ID\",\"client_secret\":\"$AZURE_CLIENT_SECRET\"}" \
            --region $REGION 2>/dev/null || \
        aws secretsmanager update-secret \
            --secret-id "/grafana/sso/azure-oauth2" \
            --secret-string "{\"tenant_id\":\"$AZURE_TENANT_ID\",\"client_id\":\"$AZURE_APP_ID\",\"client_secret\":\"$AZURE_CLIENT_SECRET\"}" \
            --region $REGION
        
        echo -e "${GREEN}✓ Azure AD OAuth2 configuration stored${NC}"
        ;;
        
    *)
        echo -e "${RED}Error: Unknown SSO provider: $SSO_PROVIDER${NC}"
        echo "Supported providers: SAML, OAUTH2_GOOGLE, OAUTH2_GITHUB, OAUTH2_AZURE"
        exit 1
        ;;
esac

# Store SSO provider
aws ssm put-parameter \
    --name "/grafana/sso/provider" \
    --value "$SSO_PROVIDER" \
    --type "String" \
    --overwrite \
    --region $REGION

echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Access Grafana at: $GRAFANA_ENDPOINT"
echo "2. Navigate to Administration > Authentication > Configure OAuth2"
echo "3. Enter the credentials stored in AWS Secrets Manager"
echo "4. Test the SSO configuration"
echo ""
echo -e "${GREEN}SSO setup completed! ✓${NC}"
