# Quick Start Guide

Быстрый старт для развертывания AWS Managed Grafana с CloudWatch и SNS уведомлениями.

## Шаг 1: Предварительные требования

### Локально установить:
```bash
# AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Python 3.9+
python3 --version

# Установить зависимости
pip install -r requirements.txt
```

### AWS Credentials
```bash
# Добавить AWS credentials
aws configure
# или
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"
export AWS_REGION="us-east-1"
```

## Шаг 2: Подготовка параметров

### Отредактировать параметры для нужного окружения:

**Для dev:**
```bash
vi parameters/dev-parameters.json
# Изменить:
# - GrafanaAdminPassword (нужен пароль 12+ символов с буквами, цифрами и спецсимволами)
# - AlertEmail (адрес для уведомлений)
```

**Для uat/prod:**
```bash
vi parameters/uat-parameters.json   # или prod-parameters.json
# Изменить те же параметры + настроить SSO
```

## Шаг 3: Валидация шаблонов

```bash
./scripts/validate-templates.sh
```

Ожидаемый результат:
```
✓ Template validation passed
✓ Valid JSON: parameters/dev-parameters.json
All validations passed!
```

## Шаг 4: Развертывание в dev

### Локальное развертывание через AWS CLI:

```bash
# Для первого развертывания
./scripts/deploy.sh dev

# Или используя AWS CLI напрямую
aws cloudformation deploy \
  --template-file templates/01-main-stack.yaml \
  --stack-name grafana-observability-dev \
  --parameter-overrides file://parameters/dev-parameters.json \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

**Время развертывания:** 5-10 минут

### Проверить статус стека:
```bash
aws cloudformation describe-stacks \
  --stack-name grafana-observability-dev \
  --query 'Stacks[0].StackStatus' \
  --output text
```

## Шаг 5: Получить доступ к Grafana

### Получить URL:
```bash
aws cloudformation describe-stacks \
  --stack-name grafana-observability-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`GrafanaWorkspaceURL`].OutputValue' \
  --output text
```

### Получить пароль администратора:
```bash
aws secretsmanager get-secret-value \
  --secret-id "/grafana/dev/admin-password" \
  --query 'SecretString' \
  --output text | jq -r '.password'
```

### Вход в Grafana:
```
Username: admin
Password: <полученный пароль>
```

## Шаг 6: Развертывание дашбордов

```bash
# Получить Grafana URL и API key
GRAFANA_URL=$(aws cloudformation describe-stacks \
  --stack-name grafana-observability-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`GrafanaWorkspaceURL`].OutputValue' \
  --output text)

GRAFANA_API_KEY=$(aws secretsmanager get-secret-value \
  --secret-id "/grafana/dev/api-key" \
  --query 'SecretString' \
  --output text | jq -r '.api_key')

# Развернуть дашборды
./scripts/deploy-dashboards.py \
  --grafana-url "$GRAFANA_URL" \
  --api-key "$GRAFANA_API_KEY" \
  --dashboards-dir dashboards/
```

Результат:
```
✓ Dashboard imported: System Metrics
✓ Dashboard imported: CloudWatch Overview
✓ Dashboard imported: Application Health
```

## Шаг 7: Настройка оповещений

```bash
# Получить SNS Topic ARN
SNS_TOPIC_ARN=$(aws cloudformation describe-stacks \
  --stack-name grafana-observability-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`GrafanaAlertsTopicArn`].OutputValue' \
  --output text)

# Создать alerts
./scripts/setup-alerts.py \
  --grafana-url "$GRAFANA_URL" \
  --api-key "$GRAFANA_API_KEY" \
  --alerts-dir alerts/ \
  --sns-topic-arn "$SNS_TOPIC_ARN"
```

## Шаг 8: Настройка SSO (опционально)

### Для Azure AD:
```bash
./scripts/setup-sso.sh dev OAUTH2_AZURE

# Ввести:
# - Azure Tenant ID
# - Azure Application (Client) ID
# - Azure Client Secret
```

### Для GitHub:
```bash
./scripts/setup-sso.sh dev OAUTH2_GITHUB

# Ввести:
# - GitHub OAuth2 Client ID
# - GitHub OAuth2 Client Secret
```

## Шаг 9: Развертывание через GitHub Actions

### Добавить GitHub Secrets:
```bash
gh secret set AWS_ACCESS_KEY_ID --body "$(aws configure get aws_access_key_id)"
gh secret set AWS_SECRET_ACCESS_KEY --body "$(aws configure get aws_secret_access_key)"
gh secret set AWS_REGION --body "us-east-1"
gh secret set GRAFANA_API_KEY --body "$GRAFANA_API_KEY"
```

### Commit и push:
```bash
git add .
git commit -m "Initial Grafana infrastructure setup"
git push origin main
```

Workflow автоматически запустится и:
- Валидирует CloudFormation templates
- Развертывает стек в dev
- Развертывает дашборды
- Создает alert rules

## Полезные команды

### Просмотреть логи Lambda:
```bash
aws logs tail /aws/lambda/grafana-dev-install-plugins --follow
```

### Обновить стек:
```bash
./scripts/deploy.sh dev
```

### Удалить стек:
```bash
aws cloudformation delete-stack --stack-name grafana-observability-dev
aws cloudformation wait stack-delete-complete --stack-name grafana-observability-dev
```

### Проверить дашборды:
```bash
./scripts/configure-grafana-cli.py test --environment dev
```

## Troubleshooting

### Ошибка: "pathspec 'main' does not match"
```bash
# Добавить файл перед push
git add .
git commit -m "Initial commit"
```

### Ошибка: "Permission denied"
```bash
# Проверить AWS credentials
aws sts get-caller-identity

# Убедиться в правах на CloudFormation
```

### Grafana не создается
```bash
# Проверить events
aws cloudformation describe-stack-events \
  --stack-name grafana-observability-dev \
  --query 'StackEvents[0:5]'
```

### Дашборды не загружаются
```bash
# Проверить API key
./scripts/configure-grafana-cli.py test --environment dev

# Проверить доступность Grafana
curl -H "Authorization: Bearer $GRAFANA_API_KEY" \
  "$GRAFANA_URL/api/health"
```

## Дальнейшие шаги

1. ✅ Настроить email subscriptions для SNS topics
2. ✅ Интегрировать Slack webhooks
3. ✅ Добавить custom dashboards для вашего приложения
4. ✅ Настроить RBAC в Grafana
5. ✅ Интегрировать Prometheus data source
6. ✅ Создать на prod с approval workflow

## Документация

- [README.md](README.md) - Полная документация
- [AWS Managed Grafana docs](https://docs.aws.amazon.com/grafana/)
- [Grafana API docs](https://grafana.com/docs/grafana/latest/http_api/)
- [CloudFormation reference](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/)

## Поддержка

Для вопросов и проблем:
- GitHub Issues: https://github.com/mikhailyesman-pet/platform_grafana_cognizant/issues
- Email: mikhail.yesman@gmail.com
