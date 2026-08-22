# FolderHome Architecture Diagram

```mermaid
flowchart TB
  Human[Person at home] --> UI[Local GUI / CLI]
  UI --> Agent[Strands Agent 1.53.0]
  Agent --> Loop[Finite sequential agent loop]
  Loop --> Fixture[Deterministic fixture model\nNo credentials / no network]
  Loop -. network + data disclosure gates .-> Bedrock[Amazon Bedrock model]
  Loop --> SearchTool[search_home_documents]
  Loop --> DossierTool[build_home_theme_dossier]
  SearchTool --> LocalApp[FolderHome LocalApplication]
  DossierTool --> LocalApp
  LocalApp --> Search[Read-only document search]
  LocalApp --> Dossier[Evidence-linked topic dossier]
  Search --> KD[KnowledgeDigest local index]
  Dossier --> KD
  UI --> Domain[FolderHome domain workflows]
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
- Both agent tools reuse the same `LocalApplication` services as the local UI.
- The offline fixture and optional Bedrock model share the same agent and tool
  contracts.
- Bedrock additionally requires separate approvals for network access and
  disclosure of local search results.
- The agent-facing tools are read-only. Broader domain workflows retain their
  own sensitivity, state, output and side-effect gates.
- OS accounts and filesystem permissions form the security boundary.
  FolderHome profiles only organize household preferences.
