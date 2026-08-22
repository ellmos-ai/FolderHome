# FCSA Bridge

**English** | [Deutsch](./README.de.md)

Implemented adapter between `folderhome.plugin.v1` and the separately pinned repository `file-collect-sort-action`.

The code is available for installation at `src/folderhome/bridges/fcsa.py`. It verifies the version, Git revision, and a clean provider checkout, loads the documented FCSA Python pipeline, and performs only a dry run with a temporary shadow state. Afterwards, the Application Service translates the plan into `ellmos.home-agent.run-report.v1`.

Not implemented and still locked:

- Live execution of FCSA actions
- Production dry-run confirmation in the FCSA state
- Implicit selection of a real user folder
- Copied or modified FCSA source code
