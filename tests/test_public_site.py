import re
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


def _service_sources() -> str:
    package = ROOT / "src" / "folderhome"
    return "\n".join(
        (package / name).read_text(encoding="utf-8")
        for name in ("application/local_app.py", "local_server.py", "mcp_server.py")
    )


def test_agent_guide_only_names_routes_and_schemas_that_exist() -> None:
    """llms.txt is read by machines; a route it invents is a wrong turn, not a typo."""

    guide = (ROOT / "llms.txt").read_text(encoding="utf-8")
    service = _service_sources()

    routes = set(re.findall(r"`(?:GET|POST) (/api/v1/[^`\s?]+)", guide))
    assert len(routes) >= 10, sorted(routes)
    for route in routes:
        # A route with placeholders is matched by its literal stem.
        assert route.split("<")[0].rstrip("/") in service, route

    schemas = set(re.findall(r"`(folderhome\.[a-z-]+\.v1)`", guide))
    assert schemas, "the guide must name the schemas a caller has to send"
    for schema in schemas:
        assert schema in service, schema

    for tool in re.findall(r"`(folderhome_[a-z_]+)`", guide):
        assert f'"{tool}"' in service, tool


def test_agent_guide_carries_no_secret_and_no_real_path() -> None:
    guide = (ROOT / "llms.txt").read_text(encoding="utf-8")

    assert "C:\\" not in guide
    assert "/Users/" not in guide
    assert "/home/" not in guide
    assert not re.search(r"token=(?!<)[A-Za-z0-9_-]{16}", guide)
    assert not re.search(r"\bsk-[A-Za-z0-9_-]{16}", guide)
    assert len(guide.splitlines()) < 200


def test_published_agent_guide_matches_the_repository_one() -> None:
    published = (ROOT / "site" / "llms.txt").read_text(encoding="utf-8")
    assert published == (ROOT / "llms.txt").read_text(encoding="utf-8")
    assert "llms.txt" in (ROOT / "site" / "index.html").read_text(encoding="utf-8")
