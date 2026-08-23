# Logical resource examples

**English** | [Deutsch](./README.de.md)

[`resources.example.json`](./resources.example.json) is an intentionally small,
anonymous starter registry. Copy it to the private per-OS-account location,
create every referenced path locally, and split resources whenever a workflow
requires source, target, state, output, desktop or configuration locations to be
separate. Physical paths and secrets must never be committed.

## Purpose groups used by the master agent

| Group | Logical purposes | Required kind and operations |
|---|---|---|
| Document input | `documents.bundle.source`, `document_package.source`, `health.source`, `finance.source`, `inventory.source`, `contacts.source`, `calendar.source` | directory; `list`, `read`, and `sensitive_read` where the adapter requests it |
| Document action | `document_action.source`, `document_action.target`, `document_action.plan_output`, `document_action.state` | file source; separate directory target, output and state; `read`, `sensitive_read`, `move`, `create`, `state_write` as requested |
| Folder automation | `folder_cleanup.source`, `folder_cleanup.target`, `folder_cleanup.state`, `directory_observation.source`, `directory_observation.state`, `folder_routine.source`, `folder_routine.target`, `folder_routine.state` | separate directories; read/list on sources, create/move on targets, read/state_write on state |
| Routine queue | `routine_queue.source`, `routine_queue.target`, `routine_queue.state`, `routine_queue.output` | separate directories; queue publication never registers a scheduler |
| FCSA | `fcsa.config`, `fcsa.scan`, `fcsa.target` | configuration and scan resources are read locally; the connected adapter remains dry-run only |
| Private outputs | `documents.bundle.output`, `document_package.output`, `health.output`, `official_notice.output`, `administrative.output`, `benefits.output`, `legal.output`, `briefing.output`, `tax.output`, `artifact_studio.output`, `contract_cockpit.output`, `correspondence.output` | directory; `create` |
| Private state | `finance.state`, `inventory.state`, `contacts.state`, `calendar.state`, `tax.state`, `contract_cockpit.state` | directory; `read` plus `state_write` or `sensitive_read` where requested |
| Configuration and requests | `calendar.configuration`, `correspondence.request`, `correspondence.designs`, `correspondence.templates`, `administrative.request`, `administrative.notice`, `administrative.designs`, `administrative.templates` | file; `read`, plus `sensitive_read` for personal requests and notices |
| Social-law sources | `official_notice.source`, `benefits.profile`, `benefits.catalog`, `legal.before`, `legal.after`, `legal.interests` | file; `read`, plus `sensitive_read` for personal material |
| Daily Briefing | `briefing.weather_snapshot`, `briefing.news_snapshot`, `briefing.desktop` | snapshot files are read locally; desktop is a separate directory with `create` |

The adapter's closed request schema is authoritative. The runtime rejects an
unknown resource ID, a wrong kind, a missing operation, a cross-profile use or
an unsafe overlap before performing a domain action.
