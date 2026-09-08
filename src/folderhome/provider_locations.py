"""Locate optional local providers without changing or weakening their pins."""

from pathlib import Path


def default_provider_root(repository: Path, provider_name: str) -> Path:
    """Prefer an explicitly provisioned private checkout over a shared sibling.

    This only selects a path; bridges still verify revision, cleanliness and
    package identity. An invalid isolated target must fail there, not fall back
    to another source silently.
    """

    isolated = repository / ".providers" / provider_name
    if isolated.exists() or isolated.is_symlink():
        return isolated
    return repository.parent / provider_name
