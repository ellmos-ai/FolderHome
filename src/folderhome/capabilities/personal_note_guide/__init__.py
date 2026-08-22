"""Reusable, provider-neutral guidance for human-authored notes."""

from __future__ import annotations

from folderhome.contracts.personal_notes import PersonalNoteGuidance, PersonalNoteRequest


class SyntheticPersonalNoteGuide:
    """Deterministic no-network guide used for local tests and demonstrations."""

    provider_id = "folderhome.synthetic-personal-note-guide"
    provider_revision = "1.0.0"
    network_required = False

    def guide(
        self,
        request: PersonalNoteRequest,
        *,
        proposed_content: str,
    ) -> PersonalNoteGuidance:
        questions = [
            "Ist dies genau der Inhalt, den du als eigene Notiz bestätigen möchtest?",
            "Fehlt ein nächster Schritt, eine Entscheidung oder eine offene Frage?",
        ]
        if request.references:
            questions.append("Sind alle verknüpften Dokumente und Termine ausdrücklich gewählt?")
        suggestions = [
            "Prüfe Titel und Bereich vor dem Speichern.",
            "Trenne Tatsachen, eigene Gedanken und offene Fragen sichtbar voneinander.",
        ]
        if request.action.value == "revert":
            suggestions.append(
                "Die Rückkehr wird als neue Version gespeichert; nichts wird gelöscht."
            )
        return PersonalNoteGuidance(
            provider_id=self.provider_id,
            provider_revision=self.provider_revision,
            questions=tuple(questions),
            suggestions=tuple(suggestions),
            confirmed_content_changed=False,
            network_invoked=False,
        )
