# ruff: noqa: E501
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
    assert "verified live with Amazon Bedrock" in html
    assert "Install and run locally" in html
    assert "Lokal installieren und starten" in html

    assert "VERIFIED LIVE" in html
    assert "REVIEW PENDING" not in html
    assert "Install and run locally" in html
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

    logo = (ROOT / "site" / "assets" / "logo.svg").read_text(encoding="utf-8")
    assert "Strands Agent 1.53.0" not in logo
    assert "Gated Home Workflows" not in logo
    assert "Folder" in logo and "Home" in logo


def test_public_architecture_visual_matches_submission_source() -> None:
    assert (ROOT / "site" / "architecture.svg").read_bytes() == (
        ROOT / "docs" / "submission" / "ARCHITECTURE_DIAGRAM.svg"
    ).read_bytes()
    flow_png = ROOT / "site" / "assets" / "architecture-agent-flow.png"
    assert flow_png.exists()
    assert flow_png.stat().st_size <= 220 * 1024
    seq_png = ROOT / "site" / "assets" / "architecture-confirm-sequence.png"
    assert seq_png.exists()
    assert seq_png.stat().st_size <= 220 * 1024
    assert not (ROOT / "site" / "assets" / "architecture-agent-flow.svg").exists()
    assert not (ROOT / "site" / "assets" / "architecture-confirm-sequence.svg").exists()
    assert (ROOT / "site" / "assets" / "product-architecture.svg").read_bytes() == (
        ROOT / "docs" / "submission" / "PRODUCT_ARCHITECTURE.svg"
    ).read_bytes()


def test_architecture_slideshow_structure_and_behavior() -> None:
    html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    javascript = (ROOT / "site" / "app.js").read_text(encoding="utf-8")
    product_svg = (ROOT / "docs" / "submission" / "PRODUCT_ARCHITECTURE.svg").read_bytes()

    # Four slides defined
    slide_matches = re.findall(r'<div class="slide[^"]*"[^>]*data-index="(\d+)"', html)
    assert slide_matches == ["0", "1", "2", "3"]
    assert 'src="architecture.svg"' in html
    assert 'src="assets/architecture-agent-flow.png"' in html
    assert 'src="assets/architecture-confirm-sequence.png"' in html
    assert 'src="assets/product-architecture.svg"' in html

    # Tone attributes
    assert 'data-tone="dark"' in html
    assert 'data-tone="light"' in html

    # Navigation buttons, dots and full-size link
    assert 'id="arch-prev"' in html
    assert 'id="arch-next"' in html
    assert 'class="slideshow-dots"' in html
    assert 'id="architecture-fullsize-link"' in html

    # PRODUCT_ARCHITECTURE.svg without full-surface background rect
    assert b'<rect width="1200" height="1080" fill="#ffffff"/>' not in product_svg
    assert b'<rect width="1200" height="1080"' not in product_svg

    # Verified live text instead of review pending
    assert "VERIFIED LIVE" in html
    assert "REVIEW PENDING" not in html
    assert "AgentCore runtime on Bedrock" in html

    # No autoplay timer (setInterval not used for slideshow)
    assert "setInterval" not in javascript

    # Four architecture cards with blue gradations and pill badges in CSS
    css = (ROOT / "site" / "app.css").read_text(encoding="utf-8")
    assert ".architecture-grid article:nth-child(1)" in css
    assert "#0b1a38" in css
    assert "#0f2a5a" in css
    assert "#153578" in css
    assert "#1e40af" in css
    assert "#dbeafe" in css
    assert "#93c5fd" in css
    assert ".architecture-grid article span" in css


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
    assert 'fill="currentColor"' in badge
    assert 'fill="none"' not in badge
    assert 'data-en="cloud mode" data-de="cloud mode"' in html
    brand_markup = html.split('<a class="brand"', 1)[1].split('</a>', 1)[0]
    assert 'cloud-mode-badge' not in brand_markup
    assert 'class="cloud-mode-lane"' in html
    assert '.cloud-mode-badge[hidden] { display: none; }' in css
    assert '@keyframes cloud-wander' not in css
    assert 'justify-content: flex-end' in css
    assert '@keyframes cloud-pulse' in css
    reduced_motion = css.split('@media (prefers-reduced-motion: reduce)', 1)[1]
    assert '.cloud-mode-badge' in reduced_motion
    assert 'animation: none' in reduced_motion
    logo_svg = (ROOT / "site" / "assets" / "logo.svg").read_text(encoding="utf-8")
    rect_pattern = (
        r'<rect[^>]*width=["\']800["\'][^>]*height=["\']200["\'][^>]*fill=["\']#(?!none)[0-9a-fA-F]+["\']'
    )
    assert not re.search(rect_pattern, logo_svg)
    assert not re.search(r'<rect[^>]*fill=["\']#0A0F1D["\']', logo_svg)
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


def test_two_entry_tiles_present_with_bilingual_texts() -> None:
    html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")

    # Tile A (Hyundai i10 Case)
    assert 'id="tile-case"' in html
    assert 'data-en="Try the test case: Hyundai i10 insurance claim"' in html
    assert 'data-de="Testfall ausprobieren: Hyundai-i10-Versicherungsfall"' in html
    assert 'data-en="Start test case"' in html
    assert 'data-de="Testfall starten"' in html

    # Tile B (Free Chat in your own words)
    assert 'id="tile-chat"' in html
    assert 'data-en="Try it in your own words"' in html
    assert 'data-de="In eigenen Worten ausprobieren"' in html
    assert 'data-en="Open free chat"' in html
    assert 'data-de="Freien Chat öffnen"' in html

    # Static mode notice and back navigation
    assert 'id="chat-static-note"' in html
    assert "Free chat needs the hosted runtime." in html
    assert "Freier Chat braucht die gehostete Runtime." in html
    assert 'id="back-to-chooser"' in html
    assert 'data-en="← Options"' in html
    assert 'data-de="← Auswahl"' in html

    # Post-result banner to switch to chat mode
    assert 'id="next-mode-banner"' in html
    assert 'data-en="Now try your own question →"' in html
    assert 'data-de="Jetzt eigene Anfrage ausprobieren →"' in html

    # Tile styling: Tile A blue/pink, Tile B neon-green, enlarged typography
    css = (ROOT / "site" / "app.css").read_text(encoding="utf-8")
    assert "#1d4ed8" in css
    assert "#3b82f6" in css
    assert "#22c55e" in css
    assert "clamp(1.6rem" in css
    assert "clamp(1.05rem" in css


def test_mode_display_rules_in_css() -> None:
    css = (ROOT / "site" / "app.css").read_text(encoding="utf-8")

    # Mode chooser
    assert ':root[data-mode="chooser"] .mode-chooser { display: grid; }' in css
    assert ':root[data-mode="chooser"] .case-index { display: none; }' in css
    assert ':root[data-mode="chooser"] .chat-panel { display: none; }' in css

    # Mode case
    assert ':root[data-mode="case"] .mode-chooser { display: none; }' in css
    assert ':root[data-mode="case"] .case-index { display: block; }' in css
    assert ':root[data-mode="case"] .chat-panel { display: block; }' in css
    assert ':root[data-mode="case"] .prompt-suggestions { display: none; }' in css

    # Mode chat: workflow steps / case index are hidden
    assert ':root[data-mode="chat"] .mode-chooser { display: none; }' in css
    assert ':root[data-mode="chat"] .case-index { display: none; }' in css
    assert ':root[data-mode="chat"] .chat-panel { display: block; }' in css
    assert ':root[data-mode="chat"] .prompt-suggestions { display: flex; }' in css

    # Stacking at narrow viewport (400px / mobile)
    assert ".mode-chooser { grid-template-columns: 1fr; }" in css


def test_data_mode_switching_and_contract_via_node() -> None:
    import json
    import shutil
    import subprocess

    import pytest

    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is needed to execute JS test")

    script = """
    function makeElement() {
      const el = {
        hidden: false,
        disabled: false,
        value: "",
        textContent: "",
        dataset: {},
        childNodes: [],
        elements: [],
        replaceChildren: () => {},
        append: () => {},
        addEventListener: (evt, cb) => { el["_on_" + evt] = cb; },
        setAttribute: (k, v) => { el.dataset[k.replace(/^data-/, "")] = v; },
        classList: { add: () => {}, remove: () => {} },
        scrollIntoView: () => {},
        cloneNode: () => makeElement(),
        focus: () => {},
      };
      return el;
    }
    const elements = {};
    function getEl(sel) {
      if (!elements[sel]) elements[sel] = makeElement();
      return elements[sel];
    }

    global.window = {
      FOLDERHOME_LIVE_DEMO: { enabled: false },
      crypto: { randomUUID: () => "mock-uuid" },
      sessionStorage: {
        _data: {},
        getItem: function(k) { return this._data[k] || null; },
        setItem: function(k, v) { this._data[k] = String(v); },
      },
      localStorage: {
        _data: {},
        getItem: function(k) { return this._data[k] || null; },
        setItem: function(k, v) { this._data[k] = String(v); },
      },
    };

    global.document = {
      querySelector: (sel) => getEl(sel),
      querySelectorAll: () => [],
      createElement: () => makeElement(),
      documentElement: { lang: "en", dataset: {}, setAttribute: function(k, v) { this.dataset[k.replace(/^data-/, "")] = v; } },
    };

    eval(require("fs").readFileSync("site/app.js", "utf8")
      + "; global.setMode = setMode; global.currentMode = currentMode; global.resetDemo = resetDemo; global.updateLiveConfigUI = updateLiveConfigUI;");

    // 1. Initial mode should be "chooser"
    const initMode = global.document.documentElement.dataset.mode;

    // 2. In static mode (enabled: false), startChatBtn is disabled, chatStaticNote is visible
    const staticChatDisabled = getEl("#start-chat-btn").disabled;
    const staticNoteHidden = getEl("#chat-static-note").hidden;

    // 3. Switch to "case" mode -> promptField is prefilled with accident prompt
    global.setMode("case");
    const caseMode = global.document.documentElement.dataset.mode;
    const casePromptValue = getEl("#prompt").value;

    // 4. Switch to "chat" mode -> promptField starts empty
    global.setMode("chat");
    const chatMode = global.document.documentElement.dataset.mode;
    const chatPromptValue = getEl("#prompt").value;

    // 5. In live mode (enabled: true), startChatBtn is enabled
    global.window.FOLDERHOME_LIVE_DEMO.enabled = true;
    global.updateLiveConfigUI();
    const liveChatDisabled = getEl("#start-chat-btn").disabled;
    const liveNoteHidden = getEl("#chat-static-note").hidden;

    console.log(JSON.stringify({
      initMode,
      staticChatDisabled,
      staticNoteHidden,
      caseMode,
      casePromptContainsHyundai: casePromptValue.includes("Hyundai i10"),
      chatMode,
      chatPromptEmpty: chatPromptValue === "",
      liveChatDisabled,
      liveNoteHidden,
    }));
    """

    result = subprocess.run(
        [node, "-e", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout)
    assert data["initMode"] == "chooser"
    assert data["staticChatDisabled"] is True
    assert data["staticNoteHidden"] is False
    assert data["caseMode"] == "case"
    assert data["casePromptContainsHyundai"] is True
    assert data["chatMode"] == "chat"
    assert data["chatPromptEmpty"] is True
    assert data["liveChatDisabled"] is False
    assert data["liveNoteHidden"] is True


def test_hero_ctas_and_demo_video_thumbnail() -> None:
    html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "site" / "app.css").read_text(encoding="utf-8")

    # Local video thumbnail asset exists and is < 100 KB
    assert "assets/demo-thumb.jpg" in html
    thumb_path = ROOT / "site" / "assets" / "demo-thumb.jpg"
    assert thumb_path.exists()
    assert thumb_path.stat().st_size < 100 * 1024

    # Privacy guarantee: no external images in site files at runtime
    assert "img.youtube.com" not in html
    assert 'src="http' not in html
    site_dir = ROOT / "site"
    for site_file in site_dir.glob("*"):
        if site_file.is_file() and site_file.suffix in (".html", ".css", ".js"):
            content = site_file.read_text(encoding="utf-8")
            assert "img.youtube.com" not in content
            assert not re.search(r'<img[^>]+src=["\']https?://', content)

    # CTA 1: Guided case
    assert 'data-en="Try the guided case"' in html
    assert 'data-de="Geführten Fall ausprobieren"' in html
    assert 'href="#demo"' in html

    # CTA 2: Video thumbnail link
    assert 'class="video-thumb"' in html
    assert 'href="https://youtu.be/wPb1wBJcLjQ"' in html
    assert 'target="_blank"' in html
    assert 'rel="noopener noreferrer"' in html
    assert 'aria-label="Watch the 3-minute demo video on YouTube"' in html
    assert 'alt="FolderHome 3-minute demo video preview"' in html
    assert "3:26" in html

    # CTA 3: Install and run locally
    assert 'data-en="Install and run locally"' in html
    assert 'data-de="Lokal installieren und starten"' in html
    assert 'data-en="pip install · your own folders · your own model"' in html
    assert 'data-de="pip install · eigene Ordner · eigenes Modell"' in html
    assert 'href="https://github.com/ellmos-ai/FolderHome#quick-test-for-jurors"' in html

    # Thumbnail styling rules in CSS
    assert ".video-thumb" in css
    assert ".video-thumb-frame" in css
    assert "border: 3px solid #e11d48;" in css
    assert ".video-play-btn" in css
    assert ".video-duration" in css
    assert ".video-thumb:focus-visible" in css

    # Video tile is in right hero column (hero-visual) above case-file, not in hero-copy
    assert '<div class="hero-visual">' in html
    assert html.index('class="hero-video"') > html.index('class="hero-copy"')
    assert html.index('class="hero-video"') < html.index('class="case-file"')
    hero_copy = html.split('<div class="hero-copy">', 1)[1].split('<div class="hero-visual">', 1)[0]
    assert 'class="hero-video"' not in hero_copy
    assert ".hero-visual" in css

    # Hero buttons colors: blue for guided case, pink for install
    assert ".hero-cta .button.primary" in css
    assert "#2563eb" in css
    assert ".hero-cta .button-install" in css
    assert "#db2777" in css


def test_demo_section_headings_per_mode() -> None:
    html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "site" / "app.css").read_text(encoding="utf-8")

    # Three mode-specific headings in index.html
    assert "demo-head-chooser" in html
    assert "demo-head-case" in html
    assert "demo-head-chat" in html

    # Chooser heading
    assert 'data-en="Cloud mode"' in html
    assert 'data-de="Cloud-Modus"' in html
    assert 'data-en="Try it here in cloud mode"' in html
    assert 'data-de="Hier im Cloud-Modus ausprobieren"' in html
    assert "104 example documents" in html

    # Case heading (preserves existing text & disclosure)
    assert 'data-en="Interactive case file"' in html
    assert 'data-de="Interaktive Fallakte"' in html
    assert 'data-en="One request. Four bounded workflows."' in html
    assert 'data-de="Eine Anfrage. Vier begrenzte Workflows."' in html
    assert "Scripted synthetic walkthrough" in html

    # Chat heading
    assert 'data-en="Free chat"' in html
    assert 'data-de="Freier Chat"' in html
    assert 'data-en="Your own words, a synthetic household"' in html
    assert 'data-de="Deine Worte, ein synthetischer Haushalt"' in html
    assert "insurance, health, contracts, taxes or the calendar" in html

    # CSS display rules for the mode headings
    assert ".demo-head-case" in css
    assert ".demo-head-chat" in css
    assert ".demo-head-chooser" in css
    assert ':root[data-mode="case"] .demo-head-case' in css
    assert ':root[data-mode="chat"] .demo-head-chat' in css
    assert ':root[data-mode="case"] .demo-head-chooser' in css
    assert ':root[data-mode="chat"] .demo-head-chooser' in css



