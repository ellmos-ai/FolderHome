from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_public_site_is_bilingual_static_and_transparent() -> None:
    html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "site" / "app.css").read_text(encoding="utf-8")
    javascript = (ROOT / "site" / "app.js").read_text(encoding="utf-8")
    runtime_configuration = (ROOT / "site" / "runtime-config.js").read_text(
        encoding="utf-8"
    )

    assert '<html lang="en">' in html
    assert "Scripted synthetic walkthrough" in html
    assert 'src="architecture.svg"' in html
    assert "AgentCore cloud deployment is not claimed" in html
    assert "Run the real local demo" in html
    assert 'data-language="de"' in html
    assert 'data-theme="light"' in html
    assert "github.com/ellmos-ai/FolderHome" in html
    assert "127.0.0.1" not in html
    assert "localhost" not in html
    assert "frame-ancestors" not in html
    assert "fetch(liveConfiguration.apiBaseUrl" in javascript
    assert "if (liveConfiguration.enabled)" in javascript
    assert 'invokeLiveDemo("/reset")' not in javascript
    assert "enabled: false" in runtime_configuration
    assert 'apiBaseUrl: ""' in runtime_configuration
    assert "127.0.0.1" not in runtime_configuration
    assert "innerHTML" not in javascript
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "focus-visible" in css


def test_branch_published_site_contains_its_referenced_brand_assets() -> None:
    html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    for name in ("favicon.svg", "logo.svg", "icon.svg"):
        relative_path = f"assets/{name}"
        assert relative_path in html
        published_asset = (ROOT / "site" / relative_path).read_text(encoding="utf-8")
        canonical_asset = (ROOT / "assets" / name).read_text(encoding="utf-8")
        assert published_asset.rstrip() == canonical_asset.rstrip()


def test_public_architecture_visual_matches_submission_source() -> None:
    assert (ROOT / "site" / "architecture.svg").read_bytes() == (
        ROOT / "docs" / "submission" / "ARCHITECTURE_DIAGRAM.svg"
    ).read_bytes()
