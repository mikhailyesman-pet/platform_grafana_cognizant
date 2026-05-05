#!/usr/bin/env python3
"""
Deploy Grafana dashboards from JSON definitions
"""

import json
import os
import sys
import argparse
import requests
from pathlib import Path

class GrafanaClient:
    def __init__(self, url, api_key):
        self.url = url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        })

    def create_folder(self, title):
        """Create a Grafana folder"""
        payload = {'title': title}
        response = self.session.post(
            f'{self.url}/api/folders',
            json=payload
        )
        response.raise_for_status()
        return response.json()

    def import_dashboard(self, dashboard_json, folder_id=None, overwrite=True):
        """Import a dashboard"""
        payload = {
            'dashboard': dashboard_json,
            'overwrite': overwrite,
            'message': 'Imported via CI/CD'
        }
        
        if folder_id:
            payload['folderId'] = folder_id
        
        response = self.session.post(
            f'{self.url}/api/dashboards/db',
            json=payload
        )
        response.raise_for_status()
        return response.json()

    def get_datasources(self):
        """List all datasources"""
        response = self.session.get(f'{self.url}/api/datasources')
        response.raise_for_status()
        return response.json()

    def create_datasource(self, name, ds_type, **kwargs):
        """Create a datasource"""
        payload = {
            'name': name,
            'type': ds_type,
            'access': 'proxy',
            'isDefault': kwargs.get('is_default', False),
            **kwargs
        }
        
        response = self.session.post(
            f'{self.url}/api/datasources',
            json=payload
        )
        response.raise_for_status()
        return response.json()

def main():
    parser = argparse.ArgumentParser(description='Deploy Grafana dashboards')
    parser.add_argument('--grafana-url', required=True, help='Grafana URL')
    parser.add_argument('--api-key', required=True, help='Grafana API key')
    parser.add_argument('--dashboards-dir', default='dashboards', help='Dashboards directory')
    parser.add_argument('--folder', default='Imported', help='Grafana folder name')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()

    try:
        # Initialize Grafana client
        client = GrafanaClient(args.grafana_url, args.api_key)
        
        if args.verbose:
            print(f"Connecting to Grafana: {args.grafana_url}")
        
        # Create folder
        if args.verbose:
            print(f"Creating folder: {args.folder}")
        
        try:
            folder = client.create_folder(args.folder)
            folder_id = folder.get('id')
            print(f"✓ Folder created: {folder['title']} (ID: {folder_id})")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 409:  # Folder already exists
                # Try to get existing folder
                response = client.session.get(f'{args.grafana_url}/api/folders')
                folders = response.json()
                folder = next((f for f in folders if f['title'] == args.folder), None)
                if folder:
                    folder_id = folder['id']
                    print(f"ℹ Folder already exists: {args.folder} (ID: {folder_id})")
                else:
                    raise
            else:
                raise

        # Import dashboards
        dashboards_path = Path(args.dashboards_dir)
        if not dashboards_path.exists():
            print(f"✗ Dashboards directory not found: {args.dashboards_dir}")
            sys.exit(1)

        dashboard_files = list(dashboards_path.glob('*.json'))
        if not dashboard_files:
            print(f"✗ No dashboard files found in {args.dashboards_dir}")
            sys.exit(1)

        print(f"\nFound {len(dashboard_files)} dashboard(s) to import:")
        print("")

        successful = 0
        failed = 0

        for dashboard_file in dashboard_files:
            if args.verbose:
                print(f"Processing: {dashboard_file}")
            
            try:
                with open(dashboard_file, 'r') as f:
                    dashboard_data = json.load(f)
                
                # Handle both direct dashboard objects and wrapped objects
                if 'dashboard' in dashboard_data:
                    dashboard = dashboard_data['dashboard']
                else:
                    dashboard = dashboard_data
                
                # Ensure uid is set
                if 'uid' not in dashboard:
                    dashboard['uid'] = dashboard_file.stem
                
                result = client.import_dashboard(dashboard, folder_id=folder_id)
                print(f"✓ Dashboard imported: {result['title']} (URL: {result['url']})")
                successful += 1

            except Exception as e:
                print(f"✗ Failed to import {dashboard_file.name}: {str(e)}")
                failed += 1

        # Summary
        print("")
        print(f"Summary: {successful} imported, {failed} failed")
        
        if failed > 0:
            sys.exit(1)

    except Exception as e:
        print(f"✗ Error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
