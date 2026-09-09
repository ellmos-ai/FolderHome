"""Translate guided edits of retained receipts into exact calendar mutation requests."""

from copy import deepcopy

CONTEXT_FIELDS = (
    "configuration_resource_id",
    "accounts_resource_id",
    "credential_resource_id",
    "ledger_resource_id",
    "account_id",
    "area",
)
EDITABLE_FIELDS = frozenset(
    {"title", "start", "end", "timezone", "all_day", "location", "reminders"}
)
REQUEST_FIELDS = frozenset(
    {
        "schema",
        "profile_id",
        "execution_id",
        "version_index",
        "operation",
        "changes",
        "language",
    }
)


def calendar_edit_context(request):
    """Public resource identifiers only: never locators, secrets or creation input."""
    return {key: request[key] for key in CONTEXT_FIELDS}


def validate_edit_request(payload):
    if not isinstance(payload, dict) or set(payload) != REQUEST_FIELDS:
        raise ValueError("Terminbearbeitung enthält unbekannte oder fehlende Felder.")
    for key in REQUEST_FIELDS - {"changes", "version_index"}:
        if not isinstance(payload[key], str) or not 1 <= len(payload[key]) <= 160:
            raise ValueError("Terminbearbeitung enthält ungültige Textfelder.")
    if (
        payload["schema"] != "folderhome.calendar-event-edit-request.v1"
        or payload["language"] not in {"de", "en"}
        or payload["operation"] not in {"update", "delete"}
        or type(payload["version_index"]) is not int
        or payload["version_index"] < 0
        or not isinstance(payload["changes"], dict)
        or set(payload["changes"]) - EDITABLE_FIELDS
        or (payload["operation"] == "delete" and payload["changes"])
        or (payload["operation"] == "update" and not payload["changes"])
    ):
        raise ValueError("Terminbearbeitung benötigt eine gültige Auswahl und Operation.")
    return deepcopy(payload)


def mutation_request_from_result(payload, result):
    if (
        not result
        or result.get("profile_id") != payload["profile_id"]
        or result.get("status") != "executed"
        or result.get("workflow_id") != "calendar-connectors"
    ):
        raise ValueError("Bestätigtes Kalenderergebnis ist in diesem Profil nicht verfügbar.")
    evidence = result.get("evidence", {})
    versions = evidence.get("event_versions", [])
    context = evidence.get("calendar_edit_context")
    if (
        not isinstance(context, dict)
        or set(context) != set(CONTEXT_FIELDS)
        or not isinstance(versions, list)
        or payload["version_index"] >= len(versions)
    ):
        raise ValueError("Versionierter Termin oder Ressourcenbindung fehlt in dieser Sitzung.")
    version = versions[payload["version_index"]]
    if (
        version.get("schema") != "folderhome.google-calendar-event-version.v1"
        or version.get("event", {}).get("profile_id") != payload["profile_id"]
    ):
        raise ValueError("Terminreferenz gehört nicht zum ausgewählten Profil.")
    previous = deepcopy(version["event"])
    return {
        **deepcopy(context),
        "operation": payload["operation"],
        "previous_event": previous,
        "expected_etag": version["etag"],
        "replacement": None
        if payload["operation"] == "delete"
        else {**deepcopy(previous), **deepcopy(payload["changes"])},
    }
