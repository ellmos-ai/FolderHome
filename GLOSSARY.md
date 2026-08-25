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

## Draft Placement

Appending one prepared letter to the drafts folder of the user's own mailbox. It is not a delivery: no recipient is contacted, and the owner still sends the message themselves in their own mail program.

## Password Location

The absolute path of a local file that holds one credential. FolderHome configures the location, never the value; the file is read at execution time only and its path stays out of plans, reports and chat.

## Side-Effect

External effect such as file writing, network access, phone call, email sending or calendar entry.
