# Observability

## Recent generation summary

`GET /v1/observability/summary` reports p50 and p95 Ollama request latency and
average input/output tokens from up to the latest 1,000 model calls in the API
process. Values reset when the API restarts. This local diagnostic is not a
durable evaluation result or an estimated monetary cost.

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/v1/observability/summary" |
    ConvertTo-Json -Depth 4
```

The service can export traces to Jaeger over OTLP/HTTP. Local tracing uses the
console exporter when `NEURALNOTES_OTEL_EXPORTER_ENDPOINT` is unset.

## Local request traces

The API creates an OpenTelemetry trace for each HTTP request and exports spans
to the API terminal with the console exporter. `/v1/answer` currently records
request, retrieval, and generation spans. The generation span includes the model
name, active prompt version, abstention result, and claim count. Retrieval spans
record the number of returned passages. The generation span also records Ollama's
input and output token counts plus request and model durations when the response
includes those fields. These local-model measurements do not estimate hardware
or electricity costs.

Every response includes `X-Request-ID` and `X-Trace-ID` headers. The request ID
is used in structured logs; the trace ID identifies the OpenTelemetry trace.
Use the trace ID to match a client response to the span output in the API
terminal.

Install the project dependencies and run the API as usual:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m uvicorn neuralnotes.api:app --reload
```

Set the OTLP endpoint before starting the API to export spans to local Jaeger:

```powershell
docker compose up -d jaeger
$env:NEURALNOTES_OTEL_EXPORTER_ENDPOINT = "http://127.0.0.1:4318/v1/traces"
.\.venv\Scripts\python.exe -m uvicorn neuralnotes.api:app --reload
```

Open `http://127.0.0.1:16686` and search for the `neuralnotes` service. Request
and trace spans do not include query or document text.
