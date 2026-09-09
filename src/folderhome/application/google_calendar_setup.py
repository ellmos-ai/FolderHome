"""Bind existing private Google files through setup, without opening credentials."""

from hashlib import sha256
from pathlib import Path

from folderhome.contracts.resources import LogicalResource

_FIELDS = {"bind_private_resources", "credential_file", "ledger_dir"}
_PREFIX = "connector://google-calendar/"


def bind_google_setup_resources(raw_calendar, *, accounts, resources, config_dir, profiles_dir):
    """Add exact local grants only; conflicting persisted declarations win."""
    if not isinstance(raw_calendar, dict):
        return
    raw_accounts = raw_calendar.get("accounts", [])
    if not isinstance(raw_accounts, list):
        return  # The calendar account parser reports malformed account collections.
    normalized = {
        (item["profile_id"], item["account_id"]): item
        for item in (accounts or {}).get("accounts", [])
    }
    additions = []
    for raw in raw_accounts:
        if not isinstance(raw, dict) or not (_FIELDS & raw.keys()):
            continue
        if not raw.keys() >= _FIELDS or raw["bind_private_resources"] is not True:
            raise ValueError("Private Google-Ressourcen benötigen eine ausdrückliche Bestätigung.")
        account = normalized[(raw.get("profile_id"), raw.get("account_id"))]
        reference = account["credential_ref"]
        if (
            account["backend"] != "google"
            or account["provider_id"] != "google-calendar"
            or account["provider_revision"] != "v3"
            or not account["calendar_id"]
            or account["calendar_id"].casefold() == "primary"
            or not isinstance(reference, str)
            or not reference.startswith(_PREFIX)
        ):
            raise ValueError(
                "Google benötigt v3, eine konkrete Kalender-ID und einen Ressourcenverweis."
            )
        credential = _existing_path(raw["credential_file"], file=True)
        ledger = _existing_path(raw["ledger_dir"], file=False)
        if credential.is_relative_to(ledger):
            raise ValueError("Zugangsdaten und Ausführungsnachweis müssen getrennt sein.")
        # No setup-owned target or document/output folder may expose or replace secrets.
        if any(
            credential.is_relative_to(Path(path).resolve()) for path in (config_dir, profiles_dir)
        ):
            raise ValueError("OAuth-Datei muss außerhalb der Setup- und Profilordner liegen.")
        profile = account["profile_id"]
        ledger_id = (
            "google_ledger_"
            + sha256((profile + "\0" + account["calendar_id"]).encode("utf-8")).hexdigest()[:24]
        )
        for resource_id, purpose, kind, path, operations in (
            (
                reference[len(_PREFIX) :],
                "calendar.google_credentials",
                "file",
                credential,
                ["read"],
            ),
            (ledger_id, "calendar.connector_ledger", "directory", ledger, ["read", "state_write"]),
        ):
            LogicalResource(
                resource_id=resource_id,
                kind=kind,
                local_path=path,
                operations=frozenset(operations),
                purposes=frozenset({purpose}),
                profile_ids=frozenset({profile}),
                cloud_context="deny",
            )
            declaration = {
                "resource_id": resource_id,
                "kind": kind,
                "locator": {"type": "local_path", "path": str(path)},
                "operations": operations,
                "purposes": [purpose],
                "profile_ids": [profile],
                "cloud_context": "deny",
            }
            if any(
                item["resource_id"] != resource_id
                and profile in item["profile_ids"]
                and purpose in item["purposes"]
                and Path(item["locator"]["path"]).resolve() == path
                for item in resources["resources"] + additions
            ):
                raise ValueError("Der private Pfad besitzt bereits eine andere Google-Zuordnung.")
            previous = next(
                (
                    item
                    for item in resources["resources"] + additions
                    if item["resource_id"] == resource_id
                ),
                None,
            )
            if previous is not None:
                if previous != declaration:
                    raise ValueError(
                        "Bestehende Google-Ressourcen bleiben unverändert; "
                        "Zuordnung separat prüfen."
                    )
            else:
                additions.append(declaration)
    resources["resources"].extend(additions)


def validate_google_resource_separation(resources):
    """Check the final setup graph, including unchanged Google and new scheduler grants."""
    private = [
        item
        for item in resources["resources"]
        if {"calendar.google_credentials", "calendar.connector_ledger"} & set(item["purposes"])
    ]
    documents = [
        (Path(item["locator"]["path"]).resolve(), item["kind"])
        for item in resources["resources"]
        if any(
            purpose.endswith((".source", ".output", ".export_output", ".target"))
            for purpose in item["purposes"]
        )
    ]
    for item in private:
        path = Path(item["locator"]["path"]).resolve()
        if any(
            path == document
            or (kind == "directory" and path.is_relative_to(document))
            or (item["kind"] == "directory" and document.is_relative_to(path))
            for document, kind in documents
        ):
            raise ValueError(
                "Google-Betriebsdaten dürfen nicht in Dokument- oder Ausgabeordnern liegen."
            )


def _existing_path(raw, *, file):
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("Google-Ressourcen benötigen einen absoluten vorhandenen Pfad.")
    path = Path(raw)
    if not path.is_absolute() or any(
        item.is_symlink() or getattr(item, "is_junction", lambda: False)()
        for item in (path, *path.parents)
    ):
        raise ValueError("Google-Ressourcen dürfen keine relativen Pfade oder Links sein.")
    if not (path.is_file() if file else path.is_dir()):
        raise ValueError("Google-Ressource fehlt oder besitzt die falsche Art.")
    return path.resolve()
