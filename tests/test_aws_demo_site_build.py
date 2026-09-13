from pathlib import Path

import pytest

from deploy.aws_demo.prepare_site import _validated_api_url


def test_aws_demo_site_url_accepts_only_exact_regional_demo_endpoint() -> None:
    endpoint = "https://abc123.execute-api.eu-central-1.amazonaws.com/live/demo"

    assert _validated_api_url(endpoint) == endpoint


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://abc123.execute-api.eu-central-1.amazonaws.com/live/demo",
        "https://abc123.execute-api.us-east-1.amazonaws.com/live/demo",
        "https://abc123.execute-api.eu-central-1.amazonaws.com/live/demo/",
        "https://abc123.execute-api.eu-central-1.amazonaws.com/live/other",
        "https://abc123.execute-api.eu-central-1.amazonaws.com/live/demo?key=value",
    ],
)
def test_aws_demo_site_url_rejects_noncanonical_endpoint(endpoint: str) -> None:
    with pytest.raises(ValueError, match="API URL"):
        _validated_api_url(endpoint)


def test_aws_demo_site_builder_never_targets_tracked_site() -> None:
    script = (
        Path(__file__).parents[1] / "deploy" / "aws_demo" / "prepare_site.py"
    ).read_text(encoding="utf-8")

    assert 'default=Path("build/aws-demo-site")' in script
    assert "api_key_value_logged" in script


def test_site_build_carries_cloud_badge_and_enables_runtime(tmp_path, monkeypatch):
    import shutil

    from deploy.aws_demo import prepare_site

    root = Path(__file__).parents[1]
    shutil.copytree(root / "site", tmp_path / "site")
    monkeypatch.setattr(prepare_site, "__file__", str(tmp_path / "deploy/aws_demo/prepare_site.py"))
    assert prepare_site.main([
        "--api-base-url", "https://abc123.execute-api.eu-central-1.amazonaws.com/live/demo",
        "--api-key", "SyntheticPublicQuotaKey12345",
    ]) == 0
    output = tmp_path / "build/aws-demo-site"
    assert 'id="cloud-mode-badge"' in (output / "index.html").read_text(encoding="utf-8")
    assert "enabled: true" in (output / "runtime-config.js").read_text(encoding="utf-8")
    assert "liveConfiguration.enabled !== true" in (output / "app.js").read_text(encoding="utf-8")
