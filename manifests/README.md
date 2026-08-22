# Manifests

**English** | [Deutsch](./README.de.md)

`components/` is the current runtime authority for reusable plugins. Every manifest must satisfy `folderhome.component-manifest.v1`, pin its origin to an exact Git revision, and currently set `default_mode = "dry-run"` as well as `live_enabled = false`.

FCSA and the other runtime bridges verify the local provider checkout against this pin in addition to runtime checks. The Phase-34 manifest binds `law-checker` only for read‑only registry and source metadata; it does not declare an automatic legal‑review API. Later stack manifests will be added once additional bridge contracts are actually implemented and released separately.
