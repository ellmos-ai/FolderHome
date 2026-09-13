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
    assert "fresh AWS acceptance is pending" in html
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
        for name in (
            "application/local_app.py",
            "application/agentcore_runtime.py",
            "local_server.py",
            "mcp_server.py",
        )
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


def test_cloud_mode_badge_is_hidden_unless_runtime_is_enabled():
    import json
    import shutil
    import subprocess

    import pytest

    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is needed to execute the browser initialization")
    html = (ROOT / "site/index.html").read_text(encoding="utf-8")
    css = (ROOT / "site/app.css").read_text(encoding="utf-8")
    js = (ROOT / "site/app.js").read_text(encoding="utf-8")
    assert 'id="cloud-mode-badge" class="cloud-mode-badge" hidden' in html
    badge = html.split('id="cloud-mode-badge"', 1)[1].split('</svg>', 1)[0]
    assert '<svg' in badge and 'aria-hidden="true"' in badge
    assert 'data-en="cloud-mode" data-de="cloud-mode"' in html
    assert '.cloud-mode-badge[hidden] { display: none; }' in css
    # Execute the actual runtime initialization with every enabled input.
    initialization = js.split('const DEFAULT_PROMPTS', 1)[0]
    for config, expected in [({}, True), ({"enabled": False}, True),
                             ({"enabled": True}, False), ({"enabled": "true"}, True)]:
        script = ('const badge = {hidden: true}; const document = {querySelector: () => badge};'
                  + 'const window = {FOLDERHOME_LIVE_DEMO: ' + json.dumps(config) + '};'
                  + initialization + 'console.log(JSON.stringify(badge.hidden));')
        result = subprocess.run([node, "-e", script], capture_output=True, text=True, check=True)
        assert json.loads(result.stdout) is expected


def test_live_page_renders_generated_files_from_the_runtime_payload() -> None:
    """The runtime returns every generated file inline; the page must show and offer it."""
    html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    javascript = (ROOT / "site" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "site" / "app.css").read_text(encoding="utf-8")

    assert 'id="generated-files"' in html
    assert "payload.result && payload.result.generated_results" in javascript
    assert "function renderGeneratedFiles(" in javascript
    assert 'e.inline === true && typeof e.content === "string"' in javascript
    assert "URL.createObjectURL(decodeResult(entry))" in javascript
    assert "download.download = entry.filename" in javascript
    assert "generatedFiles.replaceChildren()" in javascript  # reset clears the files
    assert ".file-preview" in css and ".file-action" in css


def test_live_disclosure_and_synthetic_data_notes_match_contract() -> None:
    html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    javascript = (ROOT / "site" / "app.js").read_text(encoding="utf-8")

    assert (
        "This AWS-hosted page runs the real FolderHome master agent on a synthetic household of 104 example documents. External actions stay disabled; every turn is budget-metered."
        in javascript
    )
    assert (
        "Diese AWS-gehostete Seite führt den echten FolderHome-Master-Agenten auf einem synthetischen Haushalt mit 104 Beispieldokumenten aus. Externe Aktionen bleiben deaktiviert; jeder Zug ist budgetbegrenzt."
        in javascript
    )
    assert 'id="live-data-note"' in html
    assert "Synthetic household · nothing here is real data" in html
    assert "Synthetischer Haushalt · keine echten Daten" in html
    assert 'id="prompt-suggestions"' in html
    assert "Welche Unterlagen habe ich zur Krankenversicherung?" in html
    assert "Erstelle ein Dossier zu meiner KFZ-Versicherung" in html
    assert "Was steht in meinem Kalender für nächste Woche?" in html
    assert "Was kannst du für mich tun?" in html


def test_tool_events_and_model_turns_chips_rendering() -> None:
    javascript = (ROOT / "site" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "site" / "app.css").read_text(encoding="utf-8")

    assert "meta.tool_events" in javascript
    assert "tool-chips" in javascript and ".tool-chips" in css
    assert "tool-chip" in javascript and ".tool-chip" in css
    assert "model-turns-chip" in javascript and ".model-turns-chip" in css
    assert "search_home_documents" in javascript
    assert "Suche in Dokumenten" in javascript
    assert "Search documents" in javascript
    assert "model_turns" in javascript


def test_plan_card_rendered_from_plan_payload() -> None:
    javascript = (ROOT / "site" / "app.js").read_text(encoding="utf-8")
    html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")

    assert 'id="plan-steps"' in html
    assert "function renderPlan(" in javascript
    assert "plan.steps" in javascript
    assert "formatWorkflowTitle" in javascript
    assert "plan.detected_documents" in javascript
    assert "planCard.hidden = true" in javascript


def test_confirm_field_prefilled_from_confirmation_command() -> None:
    javascript = (ROOT / "site" / "app.js").read_text(encoding="utf-8")
    assert "confirmation.value = plan.confirmation_command" in javascript


def test_generated_files_rendered_after_chat_turn() -> None:
    javascript = (ROOT / "site" / "app.js").read_text(encoding="utf-8")
    # Chat submit handler triggers renderGeneratedFiles if payload has result.generated_results
    assert "payload.result && payload.result.generated_results" in javascript
    assert "renderGeneratedFiles(payload.result.generated_results)" in javascript


def test_placeholder_cards_hidden_in_live_mode() -> None:
    javascript = (ROOT / "site" / "app.js").read_text(encoding="utf-8")
    # Live mode keeps #result-grid hidden so static placeholder cards never appear
    assert "resultGrid.hidden = true;" in javascript
    live_chat_branch = javascript.split("if (liveConfiguration.enabled)")[1].split("return;")[0]
    assert "resultGrid.hidden = false;" not in live_chat_branch


def test_honest_api_error_handling_covers_status_codes() -> None:
    javascript = (ROOT / "site" / "app.js").read_text(encoding="utf-8")

    assert "status === 429" in javascript
    assert "Daily budget limit reached" in javascript
    assert "Tagesbudget erreicht" in javascript
    assert "status === 503" in javascript
    assert "status === 502" in javascript
    assert "formatApiError" in javascript


def test_live_chat_helpers_via_node() -> None:
    import json
    import shutil
    import subprocess
    import pytest

    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is needed to execute JS helper functions")
    script = """
    global.window = { FOLDERHOME_LIVE_DEMO: { enabled: false }, crypto: { randomUUID: () => "00000000" } };
    global.localStorage = { getItem: () => null, setItem: () => {} };
    const dummy = {
      hidden: false,
      replaceChildren: () => {},
      append: () => {},
      addEventListener: () => {},
      setAttribute: () => {},
      classList: { add: () => {}, remove: () => {} },
      scrollIntoView: () => {},
      cloneNode: () => dummy,
      dataset: {},
      childNodes: [],
      elements: [],
    };
    global.document = {
      querySelector: () => dummy,
      querySelectorAll: () => [],
      createElement: () => dummy,
      documentElement: { lang: "en", dataset: {} },
    };
    eval(require("fs").readFileSync("site/app.js", "utf8")
      + "; global.formatToolName = formatToolName; global.formatApiError = formatApiError; global.setLanguage = setLanguage;");
    const e429 = global.formatApiError(429);
    const e503 = global.formatApiError(503);
    const e502 = global.formatApiError(502);
    const toolLabel = global.formatToolName("search_home_documents");
    const toolFallback = global.formatToolName("custom_specialist_action");
    global.setLanguage("de");
    const toolLabelDe = global.formatToolName("search_home_documents");
    const e429De = global.formatApiError(429);
    console.log(JSON.stringify({ e429, e503, e502, toolLabel, toolFallback, toolLabelDe, e429De }));
    """
    result = subprocess.run(
        [node, "-e", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    out = json.loads(result.stdout)
    assert "budget" in out["e429"].lower()
    assert "tagesbudget" in out["e429De"].lower()
    assert "busy" in out["e503"].lower() or "initializing" in out["e503"].lower()
    assert "upstream" in out["e502"].lower()
    assert out["toolLabel"] == "Search documents"
    assert out["toolLabelDe"] == "Suche in Dokumenten"
    assert out["toolFallback"] == "Custom specialist action"

