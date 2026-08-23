# law-checker — pinned source provider and method boundary

**English** | [Deutsch](./README.de.md)

The previous synchronized checkout remains read‑only due to lag and external changes. Phase 34 instead uses a separate clean checkout of `https://github.com/ellmos-ai/law-checker.git`, pinned to revision `06fb8d57ff90638cc50f5e33c50dbba455ac6f1b`. The four provider tests passed on 2026-08-22.

The associated pointer in the central repository `https://github.com/ellmos-ai/skills.git` was checked against revision `0317f32310eed11d21f603cb6f22a689485af226`. This local checkout is also one commit behind upstream. The skill describes `law-checker` as an initial guide, not as a lawyer or reliable deadline calendar, and requires official sources for statutes.

The risk rules of the inventory support the product boundary of Phase 31: incoming legal letters and deadlines should be reviewed early, the original is retained, and unclear deadlines are escalated. The local law register currently does not cover a complete general social‑administration and social‑court law for arbitrary notice types.

Phase 34 only binds identity, registry, and source metadata via `bridges.law_checker`. The provider does not have a stable Python API for automatic legal checking; FolderHome claims no such API and does not start either the fetcher or the agent workflow. The new encapsulated legal‑change monitor processes only pre‑provided snapshots and generates non‑binding check candidates. Legal effect, affected parties, deadlines, and notification remain separate.

---
