import shutil
import subprocess
import sys
from pathlib import Path

import yaml

from deploy.aws_demo import build_proxy
from folderhome.cloud_demo.proxy import CloudDemoProxySettings

ROOT = Path(__file__).parents[1]
BOOTSTRAP = ROOT / "deploy" / "aws_demo" / "bootstrap.yaml"
APPLICATION = ROOT / "deploy" / "aws_demo" / "application.yaml"
BUILD_PROXY = ROOT / "deploy" / "aws_demo" / "build_proxy.py"
AWS_DEMO_README = ROOT / "deploy" / "aws_demo" / "README.md"
AWS_DEMO_README_DE = ROOT / "deploy" / "aws_demo" / "README.de.md"


def test_bootstrap_template_has_a_five_dollar_budget_and_secure_artifacts() -> None:
    template = BOOTSTRAP.read_text(encoding="utf-8")

    assert "AWS::Budgets::Budget" in template
    assert "MaxValue: 195" in template
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
    proxy_log_group = template.split("  ProxyLogGroup:", 1)[1].split("  DailyQuotaTable:", 1)[0]

    assert "AWS::ApiGateway::UsagePlan" in template
    assert "AWS::DynamoDB::Table" in template
    assert "Limit: 1000" in template
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
    assert "FOLDERHOME_DAILY_QUOTA_LIMIT" not in template
    assert "dynamodb:UpdateItem" in template
    assert "PAY_PER_REQUEST" in template
    assert "bedrock-agentcore:InvokeAgentRuntime" in template
    assert "runtime-endpoint/${AgentRuntimeEndpoint}" in template
    assert "Type: MOCK" in template
    assert "EnableAcceptEncodingBrotli: false" in template
    assert "EnableAcceptEncodingGzip: false" in template
    assert "DeletionPolicy: Retain" not in proxy_log_group
    assert "UpdateReplacePolicy: Retain" not in proxy_log_group


def test_proxy_build_is_pinned_reproducible_and_arm64() -> None:
    script = BUILD_PROXY.read_text(encoding="utf-8")

    assert '_BOTO3_VERSION = "1.43.78"' in script
    assert '"aarch64-manylinux2014"' in script
    assert "date_time=(2026, 8, 24, 0, 0, 0)" in script
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
        "DEPLOY_FOLDERHOME_WITH_195_USD_ALERT",
    ):
        assert invariant in english
        assert invariant in german
    assert "Tagesguthaben" in german
    assert "ausdrücklich" in german


def _application_template():
    class CloudFormationLoader(yaml.SafeLoader):
        pass

    def tagged(loader, suffix, node):
        if isinstance(node, yaml.ScalarNode):
            value = loader.construct_scalar(node)
        elif isinstance(node, yaml.SequenceNode):
            value = loader.construct_sequence(node)
        else:
            value = loader.construct_mapping(node)
        return {suffix: value}

    CloudFormationLoader.add_multi_constructor("!", tagged)
    return yaml.load(APPLICATION.read_text(encoding="utf-8"), Loader=CloudFormationLoader)


def test_template_cannot_deploy_a_proxy_without_explicit_monetary_configuration():
    template = _application_template()
    values = {
        "AgentRuntimeArn": "arn:aws:bedrock-agentcore:eu-central-1:123456789012:runtime/demo",
        "AgentRuntimeEndpoint": "budget_v4",
        "AgentRuntimeVersion": "4",
        "BudgetReviewSha256": "c" * 64,
        "BudgetTotalMicrousd": "1000000",
        "BudgetForwardMicrousd": "100000",
        "BudgetStartUtc": "2026-09-01",
        "BudgetEndUtc": "2026-09-04",
        "DailyQuotaTable": "synthetic-budget-table",
    }
    for name in values.keys() - {"DailyQuotaTable"}:
        assert "Default" not in template["Parameters"][name]
    raw = template["Resources"]["ProxyFunction"]["Properties"]["Environment"]["Variables"]
    environment = {"AWS_REGION": "eu-central-1"}
    for name, value in raw.items():
        if isinstance(value, dict):
            environment[name] = (
                values[value["Ref"]] if "Ref" in value else "https://demo.example.org"
            )
        else:
            environment[name] = value
    settings = CloudDemoProxySettings.from_environment(environment)
    assert settings.budget.total_microusd == 1000000
    assert settings.budget.forward_microusd == 100000
    assert settings.runtime_endpoint == "budget_v4"
    assert settings.runtime_version == "4"


def test_budget_table_survives_stack_deletion_or_replacement_and_proxy_cannot_reseed():
    resources = _application_template()["Resources"]
    table = resources["DailyQuotaTable"]
    assert table["DeletionPolicy"] == "Retain"
    assert table["UpdateReplacePolicy"] == "Retain"
    statements = resources["ProxyRole"]["Properties"]["Policies"][0]["PolicyDocument"]["Statement"]
    actions = []
    for statement in statements:
        action = statement["Action"]
        actions.extend([action] if isinstance(action, str) else action)
    assert "dynamodb:UpdateItem" in actions
    assert "bedrock-agentcore:GetAgentRuntimeEndpoint" in actions
    assert not {"dynamodb:PutItem", "dynamodb:DeleteItem", "dynamodb:*"}.intersection(actions)


def test_proxy_zip_imports_budget_outside_the_checkout(tmp_path, monkeypatch, capsys):
    repository = tmp_path / "isolated-source"
    source = repository / "src" / "folderhome"
    (source / "cloud_demo").mkdir(parents=True)
    shutil.copy2(ROOT / "src" / "folderhome" / "__init__.py", source / "__init__.py")
    for path in (ROOT / "src" / "folderhome" / "cloud_demo").glob("*.py"):
        shutil.copy2(path, source / "cloud_demo" / path.name)
    with monkeypatch.context() as patch:
        patch.setattr(build_proxy, "__file__", str(repository / "deploy/aws_demo/build_proxy.py"))
        # Only the external package download is substituted; real source-copy,
        # ZIP construction and isolated import remain under test.
        patch.setattr(build_proxy.subprocess, "run", lambda *args, **kwargs: None)
        assert build_proxy.main([]) == 0
    archive = repository / "build" / "aws-demo-proxy.zip"
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            "import sys; sys.path.insert(0, sys.argv[1]); "
            "from folderhome.cloud_demo.proxy import CloudDemoProxySettings; "
            "from folderhome.cloud_demo.budget import CloudDemoBudget; print('budget-import-ok')",
            str(archive),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "budget-import-ok"
