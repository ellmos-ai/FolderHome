FROM --platform=linux/arm64 python:3.12.11-slim-bookworm@sha256:519591d6871b7bc437060736b9f7456b8731f1499a57e22e6c285135ae657bf7 AS builder

WORKDIR /build
RUN python -m venv /opt/folderhome-venv
ENV PATH="/opt/folderhome-venv/bin:$PATH"
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

FROM --platform=linux/arm64 python:3.12.11-slim-bookworm@sha256:519591d6871b7bc437060736b9f7456b8731f1499a57e22e6c285135ae657bf7

RUN useradd --system --uid 10001 --create-home folderhome \
    && mkdir -p /var/lib/folderhome-agentcore \
    && chown folderhome:folderhome /var/lib/folderhome-agentcore
WORKDIR /app
COPY --from=builder /opt/folderhome-venv /opt/folderhome-venv
ENV PATH="/opt/folderhome-venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    FOLDERHOME_AGENTCORE_CONTAINER=1 \
    FOLDERHOME_AGENTCORE_WORKSPACE=/var/lib/folderhome-agentcore \
    PORT=8080
USER folderhome
EXPOSE 8080
CMD ["python", "-m", "folderhome.agentcore_server"]
