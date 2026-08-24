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

## Local preflight

```powershell
python deploy/agentcore/build_direct_code.py
python deploy/aws_demo/build_proxy.py
python deploy/aws_demo/manage.py preflight
```

Build outputs remain under ignored `build/`. Do not commit API keys, AWS account
identifiers, email addresses, generated runtime configuration, or stack outputs.

## Deployment order

1. Create the bootstrap stack with one notification email and the exact Nova Micro
   inference-profile and foundation-model ARNs.
2. Upload the versioned direct-code ZIP and Lambda proxy ZIP to the private artifact
   bucket.
3. Create the direct-code AgentCore Runtime with the bootstrap execution role.
4. Immediately update the runtime with IMDSv2 required, then wait for `READY`.
5. Create the application stack with the runtime ARN and proxy object version.
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
  --approval-token DEPLOY_FOLDERHOME_WITH_5_USD_ALERT
```

After deployment, the same approval gate permits exactly one synthetic two-request
journey and the operational readback:

```powershell
python deploy/aws_demo/manage.py verify `
  --budget-usd 5 `
  --approval-token DEPLOY_FOLDERHOME_WITH_5_USD_ALERT
```
