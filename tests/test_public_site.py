import re
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_public_site_is_bilingual_static_and_transparent() -> None:
    html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "site" / "app.css").read_text(encoding="utf-8")
    javascript = (ROOT / "site" / "app.js").read_text(encoding="utf-8")

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
    assert "fetch(" not in javascript
    assert "innerHTML" not in javascript
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "focus-visible" in css


def test_pages_workflow_publishes_only_the_bounded_site_artifact() -> None:
    workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text(
        encoding="utf-8"
    )

    assert "pages: write" in workflow
    assert "id-token: write" in workflow
    assert "cp -R site/. _site/" in workflow
    assert "cp -R assets _site/assets" in workflow
    assert "ARCHITECTURE_DIAGRAM.svg" in workflow
    assert "_site/architecture.svg" in workflow
    assert "upload-pages-artifact" in workflow
    assert "deploy-pages" in workflow
    assert re.search(r"actions/checkout@[0-9a-f]{40} # v4", workflow)
    assert re.search(r"actions/configure-pages@[0-9a-f]{40} # v5", workflow)
    assert re.search(r"actions/upload-pages-artifact@[0-9a-f]{40} # v3", workflow)
    assert re.search(r"actions/deploy-pages@[0-9a-f]{40} # v4", workflow)


def test_public_architecture_visual_matches_submission_source() -> None:
    assert (ROOT / "site" / "architecture.svg").read_bytes() == (
        ROOT / "docs" / "submission" / "ARCHITECTURE_DIAGRAM.svg"
    ).read_bytes()
