# FolderHome — Synthetic Competition Demo

**English** | [Deutsch](./DEMO.de.md)

> Fully synthetic: no real personal data, no network, and no external impact.

## 1. Document search via the Strands agent

The Strands agent searched the local document index.
- Krankenversicherung-2026.txt
- Arztbericht-Hausarzt-2026.txt

## 2. Topic dossier via the same agent loop

The Strands agent created the local topic dossier.

# Topic dossier: Health insurance

> Local references from the FolderHome document index; no legal, financial, or medical assessment.

## References

### Krankenversicherung-2026.txt

Reference for **Health insurance**: synthetic tariff note, contact and validity starting 2026.

### Arztbericht-Hausarzt-2026.txt

Synthetic medical report with reference to **Health insurance** and a reference requiring control.

## Evidence limits

The fixture model adapter makes tool selection and response reproducible. The same Strands agent can run with Amazon Bedrock after separate network and data transfer approvals; this demo run uses neither AWS credentials nor a cloud call.
