# FolderHome-AgentCore-Runtime-Adapter

[English](./README.md) | **Deutsch**

Diese optionale Deployment-Oberfläche verpackt den synthetischen Hyundai-i10-Unfallablauf
für Amazon Bedrock AgentCore Runtime. Sie verwendet den am 23. August 2026 gegen die
AWS-Dokumentation geprüften HTTP-Protokollvertrag:

- `GET /ping` gibt `{"status":"Healthy"}` zurück.
- `POST /invocations` akzeptiert `{"prompt":"..."}` oder
  `{"input":{"prompt":"..."}}`.
- Der Container lauscht nur innerhalb des AgentCore-Containers auf `0.0.0.0:8080`.
- Das Image zielt auf ARM64 und läuft ohne Root-Rechte.

Der Adapter akzeptiert ausschließlich synthetische Fixtures. Er kann keine
Haushaltsdokumente empfangen, legt keine lokalen Pfade offen und führt keine externe
Aktion aus. Sein Fail-closed-Standard ist das deterministische Fixture-Modell. Ein
Deployment kann Amazon Bedrock nur dann ausdrücklich aktivieren, wenn sowohl das
Netzwerk-Gate als auch das Gate für synthetische Cloud-Daten gesetzt sind. In diesem
Modus verwendet der FolderHome-Strands-Masteragent Amazon Nova Micro für die anfängliche
lokale Dokumentensuche. Die vier Spezialistenpläne nach der Bestätigung bleiben
deterministisch, damit Browserlatenz und Kosten begrenzt sind. Lokale Workflow-Adapter
werden erst nach dem exakten Befehl `/confirm <plan_id>` ausgeführt. Ein Einweg-Hash des
AgentCore-Runtime-Session-Headers trennt den Sitzungszustand.

## Lokaler Vertragstest

Außerhalb des Containers bindet der Server standardmäßig nur an Loopback:

```powershell
python -m folderhome.agentcore_server
curl.exe http://127.0.0.1:8080/ping
curl.exe -X POST http://127.0.0.1:8080/invocations `
  -H "Content-Type: application/json" `
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id: folderhome-local-session-000000000001" `
  -d '{"prompt":"Find my synthetic Hyundai i10 insurance."}'
```

## ARM64-Image

Vom Repository-Root aus bauen:

```bash
docker buildx build --platform linux/arm64 \
  -f deploy/agentcore/Dockerfile \
  -t folderhome-agentcore:local --load .
docker inspect folderhome-agentcore:local --format '{{.Architecture}}'
```

Erwartete Architektur: `arm64`.

## ARM64-Direct-Code

Die öffentliche Demo verwendet AgentCore Direct Code statt ECR:

```powershell
python deploy/agentcore/build_direct_code.py
python deploy/aws_demo/build_proxy.py
python deploy/aws_demo/manage.py preflight
```

Die exakte Kostenfreigabe, die minimalen Rollenrechte, die tägliche API-Quote und die
Deployment-Reihenfolge stehen in
[`deploy/aws_demo/README.de.md`](../aws_demo/README.de.md).

Dieser Container darf nicht direkt ins Internet gestellt werden. AgentCore muss TLS
beenden und die eingehende Autorisierung durchsetzen. Ein Deployment benötigt außerdem
eine minimal berechtigte Runtime-Rolle, verschlüsselte CloudWatch-Logs mit begrenzter
Aufbewahrung, begrenzten öffentlichen Traffic und eine ausdrückliche Entscheidung, bevor
AWS-Ressourcen oder Kosten entstehen.
