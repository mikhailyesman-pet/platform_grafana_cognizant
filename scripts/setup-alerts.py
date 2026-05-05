#!/usr/bin/env python3
"""
Deploy Grafana unified alerting resources from JSON definitions.
"""

import json
import argparse
import re
import sys
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

    def upsert_contact_point(self, uid, name, channel_type, settings):
        """Create or update a Grafana contact point."""
        payload = {
            'uid': uid,
            'name': name,
            'type': channel_type,
            'settings': settings,
            'isDefault': False,
            'disableResolveMessage': False
        }

        response = self.session.post(f'{self.url}/api/v1/provisioning/contact-points', json=payload)
        if response.status_code == 409:
            response = self.session.put(f'{self.url}/api/v1/provisioning/contact-points/{uid}', json=payload)
        response.raise_for_status()
        return response.json() if response.text else payload

    def upsert_notification_template(self, name):
        """Create or update a notification template."""
        template = """{{ define "sns.default.message" }}
{{ range .Alerts }}
Status: {{ .Status }}
Alert: {{ .Labels.alertname }}
Summary: {{ .Annotations.summary }}
Description: {{ .Annotations.description }}
{{ end }}
{{ end }}"""
        payload = {'name': name, 'template': template}
        response = self.session.put(f'{self.url}/api/v1/provisioning/templates/{name}', json=payload)
        response.raise_for_status()
        return response.json() if response.text else payload

    def upsert_notification_policy(self, receiver):
        """Route CloudWatch alert rules to the SNS contact point."""
        payload = {
            'receiver': receiver,
            'group_by': ['grafana_folder', 'alertname'],
            'routes': [
                {
                    'receiver': receiver,
                    'object_matchers': [['source', '=', 'cloudwatch']]
                }
            ]
        }
        response = self.session.put(f'{self.url}/api/v1/provisioning/policies', json=payload)
        response.raise_for_status()
        return response.json() if response.text else payload

    def create_folder(self, uid, title):
        """Create a folder for alert rules if it does not already exist."""
        response = self.session.post(f'{self.url}/api/folders', json={'uid': uid, 'title': title})
        if response.status_code == 409:
            response = self.session.get(f'{self.url}/api/folders/{uid}')
        response.raise_for_status()
        return response.json()

    def get_datasources(self):
        """List all datasources"""
        response = self.session.get(f'{self.url}/api/datasources')
        response.raise_for_status()
        return response.json()

    def create_datasource(self, name, region):
        """Create the CloudWatch data source used by dashboards and alerts."""
        payload = {
            'name': name,
            'type': 'cloudwatch',
            'access': 'proxy',
            'isDefault': True,
            'jsonData': {
                'authType': 'default',
                'defaultRegion': region
            }
        }
        response = self.session.post(f'{self.url}/api/datasources', json=payload)
        response.raise_for_status()
        return response.json()

    def upsert_rule_group(self, folder_uid, group_name, interval, rules):
        """Create or replace a Grafana managed alert rule group."""
        payload = {
            'name': group_name,
            'folderUID': folder_uid,
            'interval': interval,
            'rules': rules
        }
        response = self.session.put(
            f'{self.url}/api/v1/provisioning/folder/{folder_uid}/rule-groups/{group_name}',
            json=payload
        )
        response.raise_for_status()
        return response.json() if response.text else payload


def slug(value):
    return re.sub(r'[^a-z0-9-]+', '-', value.lower()).strip('-')


def find_or_create_cloudwatch_datasource(client, region):
    datasources = client.get_datasources()
    for datasource in datasources:
        if datasource.get('type') == 'cloudwatch':
            return datasource
    return client.create_datasource('CloudWatch', region)


def comparison_type(operator):
    return {
        'GreaterThanThreshold': 'gt',
        'GreaterThanOrEqualToThreshold': 'gte',
        'LessThanThreshold': 'lt',
        'LessThanOrEqualToThreshold': 'lte'
    }.get(operator, 'gt')


def build_rule(alert_file, alert_data, datasource_uid, region, environment):
    alert = alert_data.get('alert', alert_data)
    condition = alert['condition']
    title = alert.get('title', alert_file.stem)
    uid = slug(alert.get('alerting', {}).get('name', title))[:40]
    namespace = condition['namespace'].replace('grafana/application', f'grafana/{environment}/application')

    return {
        'uid': uid,
        'title': title,
        'condition': 'C',
        'data': [
            {
                'refId': 'A',
                'relativeTimeRange': {'from': 600, 'to': 0},
                'datasourceUid': datasource_uid,
                'model': {
                    'refId': 'A',
                    'region': region,
                    'namespace': namespace,
                    'metricName': condition['metricName'],
                    'statistic': condition.get('statistic', 'Average'),
                    'period': str(condition.get('period', 300)),
                    'dimensions': {},
                    'matchExact': False
                }
            },
            {
                'refId': 'B',
                'relativeTimeRange': {'from': 600, 'to': 0},
                'datasourceUid': '__expr__',
                'model': {
                    'refId': 'B',
                    'type': 'reduce',
                    'expression': 'A',
                    'reducer': 'last'
                }
            },
            {
                'refId': 'C',
                'relativeTimeRange': {'from': 600, 'to': 0},
                'datasourceUid': '__expr__',
                'model': {
                    'refId': 'C',
                    'type': 'threshold',
                    'expression': 'B',
                    'conditions': [
                        {
                            'evaluator': {
                                'params': [condition['threshold']],
                                'type': comparison_type(condition.get('comparisonOperator'))
                            },
                            'operator': {'type': 'and'},
                            'query': {'params': ['C']},
                            'reducer': {'type': 'last'},
                            'type': 'query'
                        }
                    ]
                }
            }
        ],
        'noDataState': 'NoData',
        'execErrState': 'Error',
        'for': '5m',
        'annotations': {
            'summary': title,
            'description': alert.get('description', '')
        },
        'labels': {
            'environment': environment,
            'source': 'cloudwatch',
            'severity': 'critical' if 'critical' in ' '.join(alert.get('notification', {}).get('channels', [])) else 'warning'
        },
        'isPaused': not alert.get('alerting', {}).get('enabled', True)
    }


def main():
    parser = argparse.ArgumentParser(description='Setup Grafana alerts')
    parser.add_argument('--grafana-url', required=True, help='Grafana URL')
    parser.add_argument('--api-key', required=True, help='Grafana API key')
    parser.add_argument('--alerts-dir', default='alerts', help='Alerts directory')
    parser.add_argument('--sns-topic-arn', help='SNS Topic ARN for notifications')
    parser.add_argument('--region', default='us-east-1', help='AWS region used by CloudWatch queries')
    parser.add_argument('--environment', default='dev', help='Deployment environment')
    parser.add_argument('--folder-uid', default='cloudwatch-observability', help='Grafana folder UID for alert rules')
    parser.add_argument('--folder-title', default='CloudWatch Observability', help='Grafana folder title for alert rules')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()

    try:
        client = GrafanaAlertsClient(args.grafana_url, args.api_key)
        
        if args.verbose:
            print(f"Connecting to Grafana: {args.grafana_url}")
        
        receiver_name = 'grafana-alerts-sns'
        if args.sns_topic_arn:
            if args.verbose:
                print(f"Creating SNS contact point for: {args.sns_topic_arn}")

            client.upsert_contact_point(
                uid=receiver_name,
                name=receiver_name,
                channel_type='sns',
                settings={
                    'topic_arn': args.sns_topic_arn,
                    'subject': 'Grafana alert: {{ template "sns.default.message" . }}',
                    'body': '{{ template "sns.default.message" . }}'
                }
            )
            client.upsert_notification_template('sns.default.message')
            client.upsert_notification_policy(receiver_name)
            print(f"SNS contact point configured: {receiver_name}")

        folder = client.create_folder(args.folder_uid, args.folder_title)
        datasource = find_or_create_cloudwatch_datasource(client, args.region)
        datasource_uid = datasource.get('uid')
        if not datasource_uid:
            raise RuntimeError('CloudWatch data source does not have a UID')

        alerts_path = Path(args.alerts_dir)
        if not alerts_path.exists():
            print(f"Alerts directory not found: {args.alerts_dir}")
            sys.exit(1)

        alert_files = list(alerts_path.glob('*.json'))
        if not alert_files:
            print(f"No alert files found in {args.alerts_dir}")
            sys.exit(0)

        print(f"\nFound {len(alert_files)} alert(s) to configure:")
        print("")

        rules = []
        for alert_file in alert_files:
            if args.verbose:
                print(f"Processing: {alert_file}")

            with open(alert_file, 'r') as f:
                alert_data = json.load(f)
            rule = build_rule(alert_file, alert_data, datasource_uid, args.region, args.environment)
            rules.append(rule)
            print(f"Prepared alert rule: {rule['title']}")

        client.upsert_rule_group(folder['uid'], 'cloudwatch-managed-alerts', '1m', rules)
        print("")
        print(f"Summary: {len(rules)} alert rules deployed")

    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
