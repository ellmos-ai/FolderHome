# FolderHome AgentCore Runtime adapter

**English** | [Deutsch](./README.de.md)

This optional deployment surface packages the synthetic Hyundai i10 accident journey for
Amazon Bedrock AgentCore Runtime. It uses the HTTP protocol contract verified against the AWS
documentation on 2026-08-23:

- `GET /ping` returns `{"status":"Healthy"}`.
- `POST /invocations` accepts `{"prompt":"..."}` or
  `{"input":{"prompt":"..."}}`.
- The container listens on `0.0.0.0:8080` only inside the AgentCore container.
- The image targets ARM64 and runs as a non-root user.

The adapter accepts synthetic fixtures only. It cannot receive household uploads, does not
expose local paths, and performs no external action. Its fail-closed default is the deterministic
fixture model. A deployment can explicitly enable Amazon Bedrock only when both the network gate
and the synthetic-cloud-data gate are present. In that mode, the FolderHome Strands master agent
uses Amazon Nova Micro for the initial local document search; the four post-confirmation
specialist plans remain deterministic to bound browser latency and cost. Local workflow adapters
execute only after the exact `/confirm <plan_id>` command. Session state is isolated by a one-way
hash of the AgentCore runtime session header.

## Local contract test

Outside the container, the server binds to loopback by default:

```powershell
python -m folderhome.agentcore_server
curl.exe http://127.0.0.1:8080/ping
curl.exe -X POST http://127.0.0.1:8080/invocations `
  -H "Content-Type: application/json" `
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id: folderhome-local-session-000000000001" `
  -d '{"prompt":"Find my synthetic Hyundai i10 insurance."}'
```

## ARM64 image

Build from the repository root:

```bash
docker buildx build --platform linux/arm64 \
  -f deploy/agentcore/Dockerfile \
  -t folderhome-agentcore:local --load .
docker inspect folderhome-agentcore:local --format '{{.Architecture}}'
```

Expected architecture: `arm64`.

## ARM64 direct code

The public demo uses AgentCore direct-code deployment instead of ECR:

```powershell
python deploy/agentcore/build_direct_code.py
python deploy/aws_demo/build_proxy.py
python deploy/aws_demo/manage.py preflight
```

See [`deploy/aws_demo/README.md`](../aws_demo/README.md) for the exact cost gate,
least-privilege role, daily API quota, and deployment order.

Do not expose this container directly to the internet. AgentCore must terminate TLS and enforce
inbound authorization. A deployment also requires a least-privilege runtime role, encrypted
CloudWatch logs with a retention limit, bounded public traffic, and an explicit user decision
before AWS resources or costs are created.
