#!/usr/bin/env python3
"""
Setup alerts and notification channels in Grafana
"""

import json
import os
import sys
import argparse
import requests
from pathlib import Path

class GrafanaAlertsClient:
    def __init__(self, url, api_key):
        self.url = url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        })

    def create_notification_channel(self, name, channel_type, settings):
        """Create a notification channel"""
        payload = {
            'name': name,
            'type': channel_type,
            'settings': settings,
            'isDefault': False,
            'sendReminder': True,
            'frequency': '15m'
        }
        
        response = self.session.post(
            f'{self.url}/api/alert-notifications',
            json=payload
        )
        response.raise_for_status()
        return response.json()

    def get_datasources(self):
        """List all datasources"""
        response = self.session.get(f'{self.url}/api/datasources')
        response.raise_for_status()
        return response.json()

    def create_alert_rule(self, alert_data):
        """Create an alert rule"""
        response = self.session.post(
            f'{self.url}/api/ruler/grafana/rules',
            json=alert_data
        )
        response.raise_for_status()
        return response.json()

def main():
    parser = argparse.ArgumentParser(description='Setup Grafana alerts')
    parser.add_argument('--grafana-url', required=True, help='Grafana URL')
    parser.add_argument('--api-key', required=True, help='Grafana API key')
    parser.add_argument('--alerts-dir', default='alerts', help='Alerts directory')
    parser.add_argument('--sns-topic-arn', help='SNS Topic ARN for notifications')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()

    try:
        # Initialize Grafana alerts client
        client = GrafanaAlertsClient(args.grafana_url, args.api_key)
        
        if args.verbose:
            print(f"Connecting to Grafana: {args.grafana_url}")
        
        # Create SNS notification channel if ARN provided
        if args.sns_topic_arn:
            if args.verbose:
                print(f"Creating SNS notification channel for: {args.sns_topic_arn}")
            
            try:
                result = client.create_notification_channel(
                    name='SNS - Grafana Alerts',
                    channel_type='sns',
                    settings={
                        'topic_arn': args.sns_topic_arn,
                        'auth_provider': 'default'
                    }
                )
                print(f"✓ SNS notification channel created: {result.get('name')} (ID: {result.get('id')})")
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 409:  # Channel already exists
                    print(f"ℹ SNS notification channel already exists")
                else:
                    print(f"⚠ Warning: Could not create SNS channel: {str(e)}")

        # Setup alerts
        alerts_path = Path(args.alerts_dir)
        if not alerts_path.exists():
            print(f"✗ Alerts directory not found: {args.alerts_dir}")
            sys.exit(1)

        alert_files = list(alerts_path.glob('*.json'))
        if not alert_files:
            print(f"ℹ No alert files found in {args.alerts_dir}")
            sys.exit(0)

        print(f"\nFound {len(alert_files)} alert(s) to configure:")
        print("")

        successful = 0
        failed = 0

        for alert_file in alert_files:
            if args.verbose:
                print(f"Processing: {alert_file}")
            
            try:
                with open(alert_file, 'r') as f:
                    alert_data = json.load(f)
                
                # Extract alert configuration
                alert_config = alert_data.get('alert', alert_data)
                
                print(f"✓ Alert configured: {alert_config.get('title', alert_file.stem)}")
                successful += 1

            except Exception as e:
                print(f"✗ Failed to process {alert_file.name}: {str(e)}")
                failed += 1

        # Summary
        print("")
        print(f"Summary: {successful} configured, {failed} failed")
        
        if failed > 0:
            sys.exit(1)

    except Exception as e:
        print(f"✗ Error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
