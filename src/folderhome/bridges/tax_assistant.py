"""Pinned bridge to the extracted steuer-assistent module."""

from __future__ import annotations

import json
import sqlite3
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

from folderhome.bridges._provider import (
    ProviderCheckoutError,
    load_pinned_python_modules,
    verify_checkout_revision,
)
from folderhome.contracts import PluginDescriptor
from folderhome.contracts.tax import TaxReceiptPlan

ALLOWED_CATEGORIES = frozenset(
    {
        "Arbeitsmittel",
        "Fahrtkosten",
        "Fortbildung",
        "Homeoffice",
        "Kommunikation",
        "Sonstiges",
    }
)


class TaxAssistantBridgeError(RuntimeError):
    """Raised when the pinned tax workpaper provider cannot be trusted."""


class TaxAssistantBridge:
    def __init__(
        self,
        *,
        plugin: PluginDescriptor,
        provider_root: Path,
        db_path: Path,
    ) -> None:
        if plugin.plugin_id != "steuer-assistent":
            raise TaxAssistantBridgeError("Steuerbrücke benötigt das steuer-assistent-Manifest.")
        self.plugin = plugin
        self.provider_root = provider_root.resolve()
        self.db_path = db_path.resolve()
        try:
            verify_checkout_revision(self.provider_root, plugin.source_revision)
        except ProviderCheckoutError as exc:
            raise TaxAssistantBridgeError(str(exc)) from exc

    @property
    def provider_id(self) -> str:
        return self.plugin.plugin_id

    @property
    def provider_revision(self) -> str:
        return self.plugin.source_revision

    def revision(self) -> str:
        return sha256(
            json.dumps(self._rows(), ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()

    def receipt_count(self, tax_year: int) -> int:
        return sum(1 for row in self._rows() if str(row["datum"]).startswith(f"{tax_year}-"))

    def has_plan(self, plan_id: str) -> bool:
        marker = f"FolderHome-Plan:{plan_id}"
        return any(marker in str(row.get("notiz") or "") for row in self._rows())

    def add_receipt(self, plan: TaxReceiptPlan) -> str:
        if plan.confirmed_category not in ALLOWED_CATEGORIES:
            raise TaxAssistantBridgeError("Steuerkategorie wurde nicht vom Nutzer bestätigt.")
        if self.has_plan(plan.plan_id):
            raise TaxAssistantBridgeError("Steuerbelegplan wurde bereits angewendet.")
        marker = f"FolderHome-Plan:{plan.plan_id} Dokument:{plan.request.document_id}"
        note = marker if not plan.request.note else f"{plan.request.note}\n{marker}"
        try:
            package = load_pinned_python_modules(
                plugin=self.plugin,
                provider_root=self.provider_root,
                package_name="steuer_assistent",
            )["steuer_assistent"]
            amount = Decimal(plan.request.amount_cents) / Decimal(100)
            with package.SteuerAssistent(self.db_path) as assistant:
                result = assistant.add_beleg(
                    plan.confirmed_category,
                    betrag=amount,
                    datum=plan.request.receipt_date,
                    notiz=note,
                )
        except (ProviderCheckoutError, OSError, sqlite3.Error, ValueError) as exc:
            raise TaxAssistantBridgeError(
                f"Steuerbeleg konnte nicht gespeichert werden: {exc}"
            ) from exc
        number = str(result["nummer"])
        if not self.has_plan(plan.plan_id):
            raise TaxAssistantBridgeError("Steuerbeleg bestand den Provider-Readback nicht.")
        return number

    def export_workpaper(self, tax_year: int, output_path: Path) -> Path:
        try:
            package = load_pinned_python_modules(
                plugin=self.plugin,
                provider_root=self.provider_root,
                package_name="steuer_assistent",
            )["steuer_assistent"]
            with package.SteuerAssistent(self.db_path) as assistant:
                return Path(
                    assistant.export_arbeitsunterlage(
                        jahr=tax_year,
                        out_path=output_path,
                    )
                ).resolve()
        except (ProviderCheckoutError, OSError, sqlite3.Error, ValueError) as exc:
            raise TaxAssistantBridgeError(
                f"Steuer-Arbeitsunterlage konnte nicht exportiert werden: {exc}"
            ) from exc

    def _rows(self) -> tuple[dict[str, object], ...]:
        if not self.db_path.is_file():
            return ()
        uri = f"file:{self.db_path.as_posix()}?mode=ro&immutable=1"
        try:
            connection = sqlite3.connect(uri, uri=True)
            connection.row_factory = sqlite3.Row
            columns = {
                str(row[1]) for row in connection.execute("PRAGMA table_info(belege)").fetchall()
            }
            required = {"nummer", "datum", "kategorie", "betrag_cent", "notiz"}
            if not required.issubset(columns):
                raise TaxAssistantBridgeError(
                    "Steuer-Providerstore besitzt ein unbekanntes Schema."
                )
            rows = connection.execute(
                "SELECT nummer, datum, kategorie, betrag_cent, notiz "
                "FROM belege ORDER BY datum, nummer"
            ).fetchall()
            return tuple(dict(row) for row in rows)
        except sqlite3.Error as exc:
            raise TaxAssistantBridgeError(f"Steuer-Providerstore ist nicht lesbar: {exc}") from exc
        finally:
            if "connection" in locals():
                connection.close()
