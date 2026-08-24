from pathlib import Path

ROOT = Path(__file__).parents[1]
BOOTSTRAP = ROOT / "deploy" / "aws_demo" / "bootstrap.yaml"
APPLICATION = ROOT / "deploy" / "aws_demo" / "application.yaml"
BUILD_PROXY = ROOT / "deploy" / "aws_demo" / "build_proxy.py"
AWS_DEMO_README = ROOT / "deploy" / "aws_demo" / "README.md"
AWS_DEMO_README_DE = ROOT / "deploy" / "aws_demo" / "README.de.md"


def test_bootstrap_template_has_a_five_dollar_budget_and_secure_artifacts() -> None:
    template = BOOTSTRAP.read_text(encoding="utf-8")

    assert "AWS::Budgets::Budget" in template
    assert "MaxValue: 5" in template
    assert "NotificationType: FORECASTED" in template
    assert "AWS::KMS::Key" not in template
    assert "BlockPublicAcls: true" in template
    assert "RestrictPublicBuckets: true" in template
    assert "VersioningConfiguration" in template
    assert "bedrock:InvokeModel" in template
    assert "s3:GetObjectVersion" in template
    assert "logs:PutResourcePolicy" in template
    assert "xray:GetSamplingRules" in template
    assert "arn:${AWS::Partition}:bedrock:*::foundation-model/*" not in template


def test_application_template_bounds_public_traffic_and_keeps_site_private() -> None:
    template = APPLICATION.read_text(encoding="utf-8")
    proxy_log_group = template.split("  ProxyLogGroup:", 1)[1].split(
        "  DailyQuotaTable:", 1
    )[0]

    assert "AWS::ApiGateway::UsagePlan" in template
    assert "AWS::DynamoDB::Table" in template
    assert "Limit: 20" in template
    assert "Period: DAY" in template
    assert "ApiKeyRequired: true" in template
    assert "ReservedConcurrentExecutions" not in template
    assert "ThrottlingBurstLimit: 2" in template
    assert "ThrottlingRateLimit: 0.2" in template
    assert "RetentionInDays: 7" in template
    assert "AWS::CloudFront::OriginAccessControl" in template
    assert "BlockPublicAcls: true" in template
    assert "RestrictPublicBuckets: true" in template
    assert "FOLDERHOME_PUBLIC_ORIGIN" in template
    assert "FOLDERHOME_DAILY_QUOTA_LIMIT" in template
    assert "dynamodb:UpdateItem" in template
    assert "PAY_PER_REQUEST" in template
    assert "bedrock-agentcore:InvokeAgentRuntime" in template
    assert "runtime-endpoint/DEFAULT" in template
    assert "Type: MOCK" in template
    assert "EnableAcceptEncodingBrotli: false" in template
    assert "EnableAcceptEncodingGzip: false" in template
    assert "DeletionPolicy: Retain" not in proxy_log_group
    assert "UpdateReplacePolicy: Retain" not in proxy_log_group


def test_proxy_build_is_pinned_reproducible_and_arm64() -> None:
    script = BUILD_PROXY.read_text(encoding="utf-8")

    assert '_BOTO3_VERSION = "1.43.78"' in script
    assert '"aarch64-manylinux2014"' in script
    assert 'date_time=(2026, 8, 24, 0, 0, 0)' in script
    assert '"folderhome.cloud_demo.proxy.lambda_handler"' in script


def test_aws_demo_documentation_is_english_first_and_bilingual() -> None:
    english = AWS_DEMO_README.read_text(encoding="utf-8")
    german = AWS_DEMO_README_DE.read_text(encoding="utf-8")

    assert "**English** | [Deutsch](./README.de.md)" in english
    assert "[English](./README.md) | **Deutsch**" in german
    for invariant in (
        "python deploy/agentcore/build_direct_code.py",
        "python deploy/aws_demo/build_proxy.py",
        "python deploy/aws_demo/manage.py preflight",
        "python deploy/aws_demo/manage.py verify",
        "DEPLOY_FOLDERHOME_WITH_5_USD_ALERT",
    ):
        assert invariant in english
        assert invariant in german
    assert "höchstens" in german
    assert "ausdrücklich" in german
