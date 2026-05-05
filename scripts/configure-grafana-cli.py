#!/usr/bin/env python3
"""
Grafana CLI Configuration Tool
Manages Grafana API access and basic operations
"""

import json
import os
import sys
import argparse
import boto3
import requests
from pathlib import Path
from typing import Optional, Dict

class GrafanaConfig:
    def __init__(self, environment: str = 'dev', region: str = 'us-east-1'):
        self.environment = environment
        self.region = region
        self.ssm_client = boto3.client('ssm', region_name=region)
        self.secrets_client = boto3.client('secretsmanager', region_name=region)

    def get_workspace_url(self) -> str:
        """Get Grafana workspace URL from Parameter Store"""
        try:
            response = self.ssm_client.get_parameter(
                Name=f'/grafana/workspace-endpoint/{self.environment}'
            )
            return response['Parameter']['Value']
        except self.ssm_client.exceptions.ParameterNotFound:
            raise Exception(f"Grafana workspace not found for environment: {self.environment}")

    def get_api_key(self) -> str:
        """Get Grafana API key from Secrets Manager"""
        try:
            response = self.secrets_client.get_secret_value(
                SecretId=f'/grafana/{self.environment}/api-key'
            )
            secret = json.loads(response['SecretString'])
            return secret.get('api_key')
        except self.secrets_client.exceptions.ResourceNotFoundException:
            raise Exception(f"API key not found for environment: {self.environment}")

    def test_connection(self) -> bool:
        """Test connection to Grafana"""
        url = self.get_workspace_url()
        api_key = self.get_api_key()
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(f'{url}/api/health', headers=headers)
        return response.status_code == 200

    def import_dashboard(self, dashboard_file: str, overwrite: bool = True) -> Dict:
        """Import a dashboard from JSON file"""
        url = self.get_workspace_url()
        api_key = self.get_api_key()
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        with open(dashboard_file, 'r') as f:
            dashboard_data = json.load(f)
        
        # Handle both direct dashboard objects and wrapped objects
        if 'dashboard' in dashboard_data:
            dashboard = dashboard_data['dashboard']
        else:
            dashboard = dashboard_data
        
        payload = {
            'dashboard': dashboard,
            'overwrite': overwrite,
            'message': 'Imported via CLI'
        }
        
        response = requests.post(
            f'{url}/api/dashboards/db',
            headers=headers,
            json=payload
        )
        
        if response.status_code not in [200, 201]:
            raise Exception(f"Failed to import dashboard: {response.text}")
        
        return response.json()

def main():
    parser = argparse.ArgumentParser(description='Grafana CLI Configuration Tool')
    parser.add_argument('--environment', '-e', default='dev', help='Environment (dev/uat/prod)')
    parser.add_argument('--region', '-r', default='us-east-1', help='AWS region')
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Test connection command
    test_parser = subparsers.add_parser('test', help='Test Grafana connection')
    
    # Import dashboard command
    import_parser = subparsers.add_parser('import', help='Import dashboard')
    import_parser.add_argument('dashboard_file', help='Dashboard JSON file')
    import_parser.add_argument('--no-overwrite', action='store_true', help='Do not overwrite existing dashboard')
    
    # List command
    list_parser = subparsers.add_parser('config', help='Show configuration')
    
    args = parser.parse_args()
    
    try:
        config = GrafanaConfig(environment=args.environment, region=args.region)
        
        if args.command == 'test':
            print(f"Testing connection to Grafana ({args.environment})...")
            if config.test_connection():
                print("✓ Connection successful!")
                return 0
            else:
                print("✗ Connection failed!")
                return 1
        
        elif args.command == 'import':
            print(f"Importing dashboard: {args.dashboard_file}")
            result = config.import_dashboard(
                args.dashboard_file,
                overwrite=not args.no_overwrite
            )
            print(f"✓ Dashboard imported: {result.get('title', 'Unknown')}")
            print(f"  URL: {result.get('url', 'N/A')}")
            return 0
        
        elif args.command == 'config':
            print(f"\nGrafana Configuration ({args.environment}):")
            print(f"  Workspace URL: {config.get_workspace_url()}")
            print(f"  API Key: {config.get_api_key()[:10]}***")
            print()
            return 0
        
        else:
            parser.print_help()
            return 0
    
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
