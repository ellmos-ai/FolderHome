from folderhome import contracts


def test_run_status_rejects_states_outside_the_public_contract() -> None:
    expected = {
        "planned",
        "executed",
        "skipped",
        "blocked",
        "failed",
        "undone",
    }

    assert {status.value for status in contracts.RunStatus} == expected


def test_plugin_descriptor_serializes_capability_and_provenance() -> None:
    capability = contracts.CapabilityDescriptor(
        capability_id="documents.collect_sort",
        title="Dokumente sammeln und sortieren",
        side_effects=(contracts.SideEffect.FILESYSTEM_WRITE,),
        dry_run_supported=True,
        gate_required=True,
    )
    plugin = contracts.PluginDescriptor(
        plugin_id="file-collect-sort-action",
        name="file-collect-sort-action",
        version="0.1.0",
        source_repository="https://github.com/ellmos-ai/file-collect-sort-action.git",
        source_revision="8ebac2739c11c6a041abdd7b30131cef648b4753",
        license_id="MIT",
        interface_version="folderhome.plugin.v1",
        capabilities=(capability,),
    )

    assert plugin.to_dict() == {
        "id": "file-collect-sort-action",
        "name": "file-collect-sort-action",
        "version": "0.1.0",
        "source": {
            "repository": "https://github.com/ellmos-ai/file-collect-sort-action.git",
            "revision": "8ebac2739c11c6a041abdd7b30131cef648b4753",
        },
        "license": "MIT",
        "interface_version": "folderhome.plugin.v1",
        "capabilities": [
            {
                "id": "documents.collect_sort",
                "title": "Dokumente sammeln und sortieren",
                "side_effects": ["filesystem.write"],
                "dry_run_supported": True,
                "gate_required": True,
            }
        ],
    }


def test_run_report_payload_preserves_the_audit_contract() -> None:
    evidence = contracts.EvidenceRef(
        kind="synthetic.fixture",
        uri="fixture://success",
        sha256="a" * 64,
    )
    action = contracts.ActionEvent(
        action_id="run_demo:0001",
        sequence=1,
        name="synthetic.inspect",
        status=contracts.RunStatus.EXECUTED,
        side_effects=(),
        gate=contracts.GateDecision(required=False, granted=True, reason="no side effect"),
        evidence=(evidence,),
        undo=contracts.UndoDescriptor(supported=False, action=None),
        message="Synthetische Prüfung abgeschlossen.",
    )
    report = contracts.RunReport(
        run_id="run_demo",
        started_at="2026-08-21T16:30:00Z",
        finished_at="2026-08-21T16:30:01Z",
        status=contracts.RunStatus.EXECUTED,
        plugin_id="folderhome.synthetic",
        capability_id="synthetic.inspect",
        dry_run=True,
        provider=contracts.ProviderProvenance(
            plugin_id="folderhome.synthetic",
            version="0.1.0",
            source_repository="local://folderhome",
            source_revision="working-tree",
        ),
        actions=(action,),
        decisions=(),
    )

    assert report.to_dict() == {
        "schema": "ellmos.home-agent.run-report.v1",
        "run_id": "run_demo",
        "started_at": "2026-08-21T16:30:00Z",
        "finished_at": "2026-08-21T16:30:01Z",
        "status": "executed",
        "plugin_id": "folderhome.synthetic",
        "capability_id": "synthetic.inspect",
        "dry_run": True,
        "provider": {
            "plugin_id": "folderhome.synthetic",
            "version": "0.1.0",
            "source_repository": "local://folderhome",
            "source_revision": "working-tree",
        },
        "actions": [
            {
                "action_id": "run_demo:0001",
                "sequence": 1,
                "name": "synthetic.inspect",
                "status": "executed",
                "side_effects": [],
                "gate": {
                    "required": False,
                    "granted": True,
                    "reason": "no side effect",
                },
                "evidence": [
                    {
                        "kind": "synthetic.fixture",
                        "uri": "fixture://success",
                        "sha256": "a" * 64,
                    }
                ],
                "undo": {"supported": False, "action": None},
                "message": "Synthetische Prüfung abgeschlossen.",
            }
        ],
        "decisions": [],
    }


def test_decision_card_keeps_human_choice_separate_from_execution_status() -> None:
    decision = contracts.DecisionCard(
        decision_id="decision_live_call",
        title="Echten Anruf starten?",
        question="Darf FolderHome den freigegebenen Telefon-Connector verwenden?",
        status=contracts.DecisionStatus.PENDING,
        options=("approve_once", "reject"),
        selected=None,
    )

    assert decision.to_dict() == {
        "decision_id": "decision_live_call",
        "title": "Echten Anruf starten?",
        "question": "Darf FolderHome den freigegebenen Telefon-Connector verwenden?",
        "status": "pending",
        "options": ["approve_once", "reject"],
        "selected": None,
    }
