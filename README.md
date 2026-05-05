# AWS Managed Grafana with CloudFormation

Полное решение для развертывания AWS Managed Grafana с интеграцией CloudWatch, SSO, плагинами и автоматизацией через GitHub Actions.

## Архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│                     GitHub Repository                           │
│  ├─ CloudFormation templates                                    │
│  ├─ Lambda custom resources                                     │
│  ├─ Grafana dashboards & alerts (JSON)                          │
│  └─ GitHub Actions workflows                                    │
└──────────────────────────┬──────────────────────────────────────┘
                           │ On push to main
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    GitHub Actions CI/CD                         │
│  ├─ Deploy CloudFormation stack                                 │
│  ├─ Execute Lambda custom resources                             │
│  ├─ Deploy dashboards & alerts to Grafana                       │
│  └─ Setup SNS notifications                                     │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      AWS Services                               │
│  ├─ AWS Managed Grafana                                         │
│  │  ├─ Grafana instance with plugins                           │
│  │  ├─ SSO integration (SAML/OAuth2)                            │
│  │  └─ Dashboards & Alert rules                                 │
│  │                                                              │
│  ├─ CloudWatch                                                  │
│  │  ├─ Log Groups                                               │
│  │  ├─ Custom Metrics                                           │
│  │  └─ Composite Alarms                                         │
│  │                                                              │
│  ├─ SNS Topics                                                  │
│  │  └─ Alert notifications                                      │
│  │                                                              │
│  └─ IAM Roles & Policies                                        │
│     ├─ Grafana service role                                     │
│     └─ Lambda execution role                                    │
└─────────────────────────────────────────────────────────────────┘
```

## Структура проекта

```
grafana_init/
├── README.md                          # Этот файл
├── parameters/
│   ├── dev-parameters.json           # Параметры для dev окружения
│   ├── uat-parameters.json           # Параметры для UAT окружения
│   └── prod-parameters.json          # Параметры для prod окружения
├── templates/
│   ├── 01-main-stack.yaml            # Основной CloudFormation стек
│   ├── 02-grafana-stack.yaml         # Grafana и плагины
│   ├── 03-cloudwatch-stack.yaml      # CloudWatch конфигурация
│   ├── 04-sns-stack.yaml             # SNS и уведомления
│   └── 05-iam-roles.yaml             # IAM роли и политики
├── lambdas/
│   ├── install-grafana-plugins/      # Lambda для установки плагинов
│   │   ├── lambda_function.py
│   │   ├── requirements.txt
│   │   └── index.py
│   ├── setup-grafana-sso/            # Lambda для SSO интеграции
│   │   ├── lambda_function.py
│   │   ├── requirements.txt
│   │   └── index.py
│   ├── deploy-dashboards/            # Lambda для развертывания дашбордов
│   │   ├── lambda_function.py
│   │   ├── requirements.txt
│   │   └── index.py
│   └── setup-alerts/                 # Lambda для создания алертов
│       ├── lambda_function.py
│       ├── requirements.txt
│       └── index.py
├── dashboards/
│   ├── system-metrics.json           # Dashboard для системных метрик
│   ├── cloudwatch-overview.json      # CloudWatch обзор
│   └── application-health.json       # Health check dashboard
├── alerts/
│   ├── high-cpu-alert.json
│   ├── high-memory-alert.json
│   └── log-error-alert.json
├── github-actions/
│   └── deploy.yml                    # GitHub Actions workflow
├── scripts/
│   ├── deploy.sh                     # Скрипт развертывания
│   ├── setup-sso.sh                  # Настройка SSO
│   ├── validate-templates.sh         # Валидация CloudFormation
│   └── configure-grafana-cli.py      # CLI для Grafana API
└── .gitignore                        # Git ignore rules
```

## Компоненты решения

### 1. CloudFormation Стеки

#### `01-main-stack.yaml`
- Корневой стек для оркестрации
- Вызывает вложенные стеки
- Параметры конфигурации

#### `02-grafana-stack.yaml`
- AWS Managed Grafana instance
- Service role с необходимыми правами
- Custom resources для установки плагинов и SSO

#### `03-cloudwatch-stack.yaml`
- Log Groups
- Custom Metrics
- Metric Filters
- Composite Alarms

#### `04-sns-stack.yaml`
- SNS Topics для алертов
- Email subscriptions
- SMS/Slack интеграция (опционально)

#### `05-iam-roles.yaml`
- IAM roles для Grafana
- IAM roles для Lambda functions
- Service-linked roles

### 2. Lambda Custom Resources

#### `install-grafana-plugins`
Устанавливает плагины в Grafana:
- alexanderzobnin-zabbix-app
- grafana-piechart-panel
- grafana-worldmap-panel
- grafana-clock-panel
- grafana-simple-json-datasource

#### `setup-grafana-sso`
Настраивает SSO:
- SAML 2.0 интеграция
- OAuth2 (Google, GitHub, Azure AD)
- API key для dashboard provisioning

#### `deploy-dashboards`
Развертывает dashboards:
- Загружает JSON definitions
- Создает папки
- Настраивает data sources

#### `setup-alerts`
Создает alert rules и notification channels:
- Grafana alert rules
- SNS notification channels
- Webhook integrations

### 3. GitHub Actions Workflow

Автоматизирует:
- Валидацию CloudFormation templates
- Развертывание stacks (with approval)
- Запуск Lambda functions
- Развертывание dashboards
- Создание алертов

## Предварительные требования

### AWS Account
- [ ] AWS Account с IAM credentials
- [ ] CloudFormation permissions
- [ ] Grafana service limits (убедитесь в квотах)

### GitHub
- [ ] GitHub repository с доступом к Actions
- [ ] AWS credentials добавлены как GitHub Secrets:
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`
  - `AWS_REGION` (default: us-east-1)
  - `GRAFANA_ADMIN_PASSWORD` (сгенерируется, если не указана)

### Локально
- [ ] AWS CLI v2
- [ ] Python 3.9+
- [ ] cfn-lint (для валидации)
- [ ] jq (для JSON parsing)

## Установка и развертывание

### 1. Локальное тестирование

```bash
# Клонировать репозиторий
git clone https://github.com/mikhailyesman-pet/platform_grafana_cognizant.git
cd platform_grafana_cognizant

# Установить зависимости
pip install -r requirements.txt

# Валидировать CloudFormation templates
./scripts/validate-templates.sh

# Развернуть локально (если нужно)
aws cloudformation validate-template --template-body file://templates/01-main-stack.yaml
```

### 2. Первоначальное развертывание через AWS Console

```bash
# 1. Загрузить основной стек через AWS CloudFormation Console
# Template: templates/01-main-stack.yaml
# Stack Name: grafana-observability-stack
# Parameters: указать из parameters/prod-parameters.json

# 2. Дождаться создания всех ресурсов
# 3. Получить outputs (Grafana URL, API key и т.д.)
```

### 3. GitHub Actions - Автоматическое развертывание

```bash
# 1. Создать GitHub Secrets:
gh secret set AWS_ACCESS_KEY_ID --body "$(aws sts get-caller-identity | jq -r .Account)"
gh secret set AWS_SECRET_ACCESS_KEY --body "your-secret-key"
gh secret set AWS_REGION --body "us-east-1"

# 2. Push в main branch
git add -A
git commit -m "Setup Grafana infrastructure"
git push -u origin main

# 3. GitHub Actions автоматически запустится и:
# - Валидирует templates
# - Создает/обновляет stack (requires approval)
# - Развертывает dashboards
# - Создает alerts
```

## Конфигурация параметров

### dev-parameters.json
```json
{
  "ParameterKey": "EnvironmentName",
  "ParameterValue": "dev"
}
```

### uat-parameters.json
```json
{
  "ParameterKey": "EnvironmentName",
  "ParameterValue": "uat"
}
```

### prod-parameters.json
```json
{
  "ParameterKey": "EnvironmentName",
  "ParameterValue": "prod"
}
```

## Использование

### Добавить новый Dashboard

1. Создать JSON файл в `dashboards/`:
```bash
# Экспортировать из UI Grafana или создать вручную
cp dashboards/template.json dashboards/my-dashboard.json
```

2. Добавить в стек через Lambda:
```bash
./scripts/deploy-dashboards.sh dashboards/my-dashboard.json
```

### Добавить новый Alert

1. Создать JSON в `alerts/`:
```bash
cp alerts/template.json alerts/my-alert.json
```

2. Развернуть:
```bash
./scripts/setup-alerts.sh alerts/my-alert.json
```

### SSO интеграция

1. Отредактировать параметры в `templates/02-grafana-stack.yaml`:
```yaml
SSOProvider: SAML  # или OAuth2
SSOConfigURL: "https://idp.example.com/saml"
```

2. Запустить Lambda:
```bash
./scripts/setup-sso.sh
```

## Мониторинг

### CloudWatch Metrics
- Grafana API response times
- Dashboard load times
- Alert trigger frequency

### Grafana Dashboards
- System Metrics Dashboard - CPU, Memory, Disk
- CloudWatch Overview - Logs, Metrics, Alarms
- Application Health - Custom metrics

### Alerts
- High CPU usage (> 80%)
- High Memory usage (> 85%)
- Log errors detected
- API latency spike

### SNS Notifications
Все alerts отправляются через SNS в:
- Email
- SMS (optional)
- Slack (через webhook)

## Полезные команды

```bash
# Получить outputs из стека
aws cloudformation describe-stacks --stack-name grafana-observability-stack --query 'Stacks[0].Outputs'

# Получить Grafana URL
aws cloudformation describe-stacks --stack-name grafana-observability-stack \
  --query 'Stacks[0].Outputs[?OutputKey==`GrafanaURL`].OutputValue' --output text

# Получить API key
aws secretsmanager get-secret-value --secret-id grafana-api-key --query 'SecretString'

# Просмотреть логи Lambda
aws logs tail /aws/lambda/install-grafana-plugins --follow

# Обновить стек
aws cloudformation update-stack --stack-name grafana-observability-stack \
  --template-body file://templates/01-main-stack.yaml \
  --parameters ParameterKey=EnvironmentName,ParameterValue=prod
```

## Troubleshooting

### Grafana не создается
```bash
# Проверить CloudFormation события
aws cloudformation describe-stack-events --stack-name grafana-observability-stack
```

### Плагины не устанавливаются
```bash
# Проверить логи Lambda
aws logs tail /aws/lambda/install-grafana-plugins --follow

# Проверить Grafana API ответы
curl -H "Authorization: Bearer $API_KEY" \
  https://grafana-id.grafana-workspace.aws-region.amazonaws.com/api/plugins
```

### Dashboards не развертываются
```bash
# Проверить API key и URL
./scripts/configure-grafana-cli.py --test

# Загрузить dashboard вручную
./scripts/configure-grafana-cli.py --import dashboards/system-metrics.json
```

## Безопасность

- [ ] API keys хранятся в AWS Secrets Manager
- [ ] Grafana admin password в Secrets Manager
- [ ] CloudFormation template параметры не содержат sensitive data
- [ ] Lambda functions имеют minimal IAM permissions
- [ ] SSO включен по умолчанию
- [ ] HTTPS обязателен для всех connections

## Costs

Приблизительные затраты в AWS:

- AWS Managed Grafana: $5-15 USD/месяц (в зависимости от tier)
- CloudWatch Logs: ~$0.50 USD/GB ingested
- CloudWatch Metrics: $0.10 USD/metric/месяц
- Lambda executions: бесплатно (в пределах free tier)
- SNS notifications: ~$0.50 USD/1M notifications

Итого: ~$20-50 USD/месяц

## Support и Contributing

- Issues: GitHub Issues
- Discussion: GitHub Discussions
- Contributing: Pull Requests welcome

## License

MIT

## Контакты

- Author: mikhailyesman
- Email: mikhail.yesman@gmail.com
- GitHub: https://github.com/mikhailyesman-pet/platform_grafana_cognizant
