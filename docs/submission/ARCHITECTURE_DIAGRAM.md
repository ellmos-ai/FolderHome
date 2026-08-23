# FolderHome Architecture Diagram

[Open the publication-ready SVG](./ARCHITECTURE_DIAGRAM.svg) ·
[Open the rendered PNG](./ARCHITECTURE_DIAGRAM.png)

![FolderHome competition architecture](./ARCHITECTURE_DIAGRAM.svg)

The diagram above is the canonical submission visual. The Mermaid source below
remains the detailed text-friendly map.

```mermaid
flowchart TB
  Human[Person at home] --> UI[Local GUI / CLI]
  Public[Public scripted showcase\nNo backend] -. orientation only .-> Human
  AgentCore[Optional AgentCore HTTP Runtime\nSynthetic sessions only] --> Agent
  UI --> Agent[FolderHome Master / Strands Agent 1.53.0]
  UI --> Memory[Bounded per-profile conversation\nProcess memory only]
  Memory --> Agent
  UI -->|New conversation or /reset| Reset[Clear retained context\nand unconfirmed profile plans]
  Reset --> Memory
  Agent --> Loop[Finite sequential agent loop]
  Loop --> Fixture[Deterministic fixture model\nNo credentials / no network]
  Loop -. network + data disclosure gates .-> Bedrock[Amazon Bedrock model]
  Loop --> SearchTool[search_home_documents]
  Loop --> DossierTool[build_home_theme_dossier]
  Loop --> CatalogTool[list_home_capabilities]
  Loop --> SpecialistTool[consult_home_specialist]
  SpecialistTool --> Specialist[Short-lived domain agent]
  Specialist --> PlanTool[One allowlisted planning tool]
  SearchTool --> LocalApp[FolderHome LocalApplication]
  DossierTool --> LocalApp
  LocalApp --> Search[Read-only document search]
  LocalApp --> Dossier[Evidence-linked topic dossier]
  Search --> KD[KnowledgeDigest local index]
  Dossier --> KD
  PlanTool --> Confirm[Exact plan hash + step confirmation]
  Confirm --> Registry[Typed executor registry]
  Registry -->|connected envelope| Domain[Existing FolderHome domain executor]
  Registry -->|not connected| Handoff[Visible handoff only]
  Domain --> Report[Authoritative domain execution report]
  Domain --> Docs[Document gardening / FCSA]
  Domain --> Home[Contacts / calendar / household]
  Domain --> Sensitive[Finance / health / administration]
  Docs --> Gates[Plan + hash + approval + audit]
  Home --> Gates
  Sensitive --> Gates
  Gates --> Effects[Explicitly gated local effects]
```

## Boundaries shown in the diagram

- The required Strands Agents loop is the agentic decision layer, not a second
  implementation of document search.
- The public site is a transparent scripted walkthrough. The token-gated local
  accident demo and the optional AgentCore adapter invoke the real synthetic
  Strands journey; neither enables external effects.
- The AgentCore adapter implements the HTTP `/ping` and `/invocations`
  contract in an ARM64 non-root container and isolates state by runtime session.
  Local contract tests do not constitute a deployed AWS endpoint claim.
- GUI and CLI call the same master service. Its direct document tools reuse the
  same `LocalApplication` services.
- Interactive GUI and CLI sessions keep bounded model-visible history per
  organizational profile in process memory only. Resetting a conversation also
  discards that profile's unconfirmed plans, but no documents or completed
  receipts.
- Semantic expert selection belongs to the configured model. The application
  resolves selected endpoints deterministically and contains no keyword router.
- Specialist agents are created on demand with one planning endpoint. Personas
  are style-only and grant no capability or permission.
- The offline fixture and optional Bedrock model share the same agent and tool
  contracts.
- Bedrock additionally requires separate approvals for network access and
  disclosure of local search results.
- Direct tools and specialist consultation perform no domain side effects. A
  separate hash-bound confirmation proves approval. Only a connected typed
  envelope may additionally produce an authoritative domain execution report.
- Without a private resource registry, connected coverage reuses personal
  notes, scheduled medication confirmation and the strictly local FindCall
  fixture. A configured registry adds 23 typed adapters covering the complete
  local document and assistance stack. All publish closed request schemas; this
  configuration reports 26 connected and three visibly unconnected endpoints.
- Only mail, external calendars and scheduler registration still need explicit
  external connector configuration with live-effect approvals.
- Broader domain workflows retain their own sensitivity, state, output and
  side-effect gates.
- OS accounts and filesystem permissions form the security boundary.
  FolderHome profiles only organize household preferences.
