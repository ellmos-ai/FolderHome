# GLOSSARY.md — FolderHome Terms

**English** | [Deutsch](./GLOSSARY.de.md)

## Bridge

New FolderHome code that translates the common plugin contract into the interface of a separately versioned component.

## Capability

A singly declared capability of a plugin including side-effects, dry-run support, and gate requirement.

## Decision Card

Machine‑readable, human‑understandable decision that remains open before an approval‑required action.

## Gate

Explicit permission check before a side-effect. Missing or unknown permission results in `blocked`, not execution.

## Run Report

Versioned JSON report of a run in schema `ellmos.home-agent.run-report.v1` with provenance, actions, evidence and decisions.

## Side-Effect

External effect such as file writing, network access, phone call, email sending or calendar entry.
