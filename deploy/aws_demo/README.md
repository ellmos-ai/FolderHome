# FolderHome public AWS demo

**English** | [Deutsch](./README.de.md)

This deployment keeps the public website static while routing only the synthetic
accident journey through an IAM-only Amazon Bedrock AgentCore Runtime. The master
turn uses Strands Agents with Amazon Nova Micro. After the exact `/confirm`, the
four local specialist plans execute deterministically so the browser request stays
bounded in cost and duration.

## Safety and cost boundary

- The demo accepts synthetic fixture data only.
- It cannot send mail, change an external calendar, call a phone number, or modify
  a visitor's files.
- The browser API key is a public quota identifier, not authentication.
- An atomic DynamoDB condition admits at most 20 valid AgentCore forwards per UTC
  day, equivalent to ten complete two-request demonstrations.
- The same transaction reserves a reviewed worst-case amount in integer
  **micro-USD**. A finite allocation is released over UTC calendar days; unspent
  entitlement carries forward, including across idle days. The end date is
  exclusive. Expired windows, missing ledgers and changed policy hashes deny access.
- The API Gateway usage-plan quota and throttle are additional best-effort shields,
  not the hard cost boundary.
- API Gateway limits bursts to two requests and 0.2 requests per second. The
  AgentCore SDK call times out after 25 seconds without retries. Function-level
  reserved concurrency is intentionally omitted because new AWS accounts can
  expose only the mandatory ten unreserved Lambda executions; the atomic
  DynamoDB admission remains the hard boundary before AgentCore.
- CloudWatch encrypts every log group at rest with its service-managed AES-256-GCM
  encryption; a customer-managed KMS key is intentionally omitted to avoid a fixed
  monthly key charge for synthetic data.
- The USD 5 AWS Budget sends alerts; it is not a hard spending stop.
- Creating or updating AWS resources requires an explicit human cost approval.

**This is a forward-reservation ledger, not an account-wide billing stop.**
The reservation must cover all billable downstream work for the reviewed runtime,
including model turns, input/output limits and runtime lifetime. A proxy timeout
does not prove that downstream work stopped, so reservations are never refunded.
Static hosting, rejected requests, logs, DynamoDB operations and other infrastructure
costs need a separately reviewed reserve and monitoring. No current credits,
prices or live deployment acceptance are implied by passing local tests.

The proxy invokes a dedicated endpoint pinned to the reviewed runtime version,
not `DEFAULT`, and checks its current version before admission. Operators must not
retarget that endpoint during service: the check and invocation are not a single
AWS transaction. Administrative mutations and compromised IAM credentials are
outside this application-level safeguard.

## Build and preflight

```powershell
python deploy/agentcore/build_direct_code.py
python deploy/aws_demo/build_proxy.py
python deploy/aws_demo/manage.py preflight
```

The two build commands are local packaging operations (dependency downloads may
occur). **`preflight` also reads AWS identity, templates and runtime/model state**;
it is not an offline test. Do not run it when AWS work is deferred.

Build outputs remain under ignored `build/`. Do not commit API keys, AWS account
identifiers, email addresses, generated runtime configuration, or stack outputs.

## Required monetary review

Before deployment, prepare a private `build/budget-review.json` using schema
`folderhome.cloud-budget-review.v1`. Required fields:

- `approved`: explicit boolean `true`, only after the account owner's review.
- `available_funds_microusd`: verified, unspent allocation; it must equal the
  approved billing-alert amount (the existing deployment gate remains USD 5).
- `other_costs_reserved_microusd`: allocation retained for non-forward costs.
- `total_microusd`, `forward_microusd`: positive integer invocation allocation
  and substantiated upper-bound reservation per forward. Their units are
  millionths of one USD; no floating-point currency is used.
- `start_utc`, `end_utc`: `YYYY-MM-DD`, start inclusive and end exclusive,
  one to 366 days. Choose the end **after the winner announcement**, not submission.
- `agentcore_zip_sha256`, `proxy_zip_sha256`: full hashes of the exact reviewed
  `build/agentcore-direct.zip` and `build/aws-demo-proxy.zip`.
- `runtime_profile_sha256`: hash of the canonical model/environment/lifecycle
  profile returned by the offline `python deploy/aws_demo/manage.py cost-profile`.
  Deployment uses that exact profile; changing the model or limits invalidates review.
- `basis`: cost derivation with dated pricing, maximum model work and runtime
  lifecycle, infrastructure allowance, current funds and shutdown evidence.

The loader rejects unknown/duplicate fields, stale artifacts, invalid amounts
and overallocated funds. It validates the record, **not the truth of its cost
estimate**. There are no ready-to-activate sample amounts. The review file's hash
is part of the deployed ledger policy. Any policy change requires explicit review
and a migration preserving spent money; it must never reset the ledger to zero.

The fixed `_budget_v1` ledger has no TTL. CloudFormation retains the table on
deletion/replacement, and the proxy cannot create or delete ledger items. Fresh
deployment uses a conditional initial create plus consistent readback before
publishing the browser configuration. The fresh-deploy command refuses an
existing application, including visible deleted-stack history. **An existing
demo needs a separately reviewed migration; deleting its table is not migration.**

The underlying atomicity and retry semantics are documented in the
[DynamoDB transaction API](https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_TransactWriteItems.html).

## Deployment order

1. Create the bootstrap stack with one notification email and the exact Nova Micro
   inference-profile and foundation-model ARNs.
2. Upload the versioned direct-code ZIP and Lambda proxy ZIP to the private artifact
   bucket.
3. Create the direct-code AgentCore Runtime with the bootstrap execution role.
4. Immediately update the runtime with IMDSv2 required, then wait for `READY`.
5. Create a dedicated version-bound endpoint and the application stack with the
   reviewed money/window parameters. Initialize and read back the persistent ledger.
6. Generate `runtime-config.js` only in the ignored site build directory, then sync
   the static site to its private S3 bucket and invalidate CloudFront.
7. Verify one complete synthetic plan-and-confirm journey through CloudFront.
8. Read back API quota, API throttling, log retention, runtime settings, and
   budget notifications before treating the deployment as complete.

The AWS site is the live demonstration. The GitHub Pages site remains a deterministic
fixture demo and never contains the live public quota key.

The deploy command is deliberately unusable without both the reviewed USD 5 alert
threshold and an exact approval token. Invoke it only after the account owner has
explicitly accepted that AWS charges can occur and that the budget is an alert rather
than a hard spending stop:

```powershell
python deploy/aws_demo/manage.py deploy `
  --budget-alert-email "ACCOUNT-OWNER-EMAIL" `
  --budget-usd 5 `
  --budget-review build/budget-review.json `
  --approval-token DEPLOY_FOLDERHOME_WITH_5_USD_ALERT
```

After deployment, the same approval gate permits exactly one synthetic two-request
journey and the operational readback:

```powershell
python deploy/aws_demo/manage.py verify `
  --budget-usd 5 `
  --budget-review build/budget-review.json `
  --approval-token DEPLOY_FOLDERHOME_WITH_5_USD_ALERT
```

`verify` checks the deployed monetary policy, remaining entitlement, runtime
version and intentionally unreserved Lambda configuration before paid probes.
It also compares the deployed Lambda code hash, versioned Runtime artifact,
IMDSv2 setting and full runtime cost profile with the approved material.
It then reads back the two reservations. This does not activate or migrate an
existing static demo, and does not certify account-wide spending or cleanup.
At the reviewed end, admission stops; resource shutdown, retained-table handling
and remaining-credit readback still require the separately approved AWS closeout.

## Migrating the existing demo to the reviewed budget

`deploy` refuses an application that already exists. An existing demo that has
never reserved money (no `_budget_v1` ledger item) is brought under the budget
with `migrate`: it uploads the current artifacts, updates the existing runtime
(IMDSv2 required, new version), creates the version-bound `budget_v<N>` endpoint,
updates the application stack with the reviewed money/window parameters and
creates the ledger conditionally. The static site is left untouched unless
`--publish-site` is given; without it the browser agent stays disabled.

```powershell
python deploy/aws_demo/manage.py migrate `
  --budget-usd 5 `
  --budget-review build/budget-review.json `
  --approval-token DEPLOY_FOLDERHOME_WITH_5_USD_ALERT
```

A ledger that already holds reserved money is refused; carrying spent money needs
its own reviewed migration.
