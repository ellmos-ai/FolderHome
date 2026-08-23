# FolderHome Architecture Diagram

```mermaid
flowchart TB
  Human[Person at home] --> UI[Local GUI / CLI]
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
