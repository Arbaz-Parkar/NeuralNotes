# Observability

## Local request traces

The API creates an OpenTelemetry trace for each HTTP request and exports spans
to the API terminal with the console exporter. `/v1/answer` currently records
request, retrieval, and generation spans. The generation span includes the model
name, active prompt version, abstention result, and claim count. Retrieval spans
record the number of returned passages.

Every response includes `X-Request-ID` and `X-Trace-ID` headers. The request ID
is used in structured logs; the trace ID identifies the OpenTelemetry trace.
Use the trace ID to match a client response to the span output in the API
terminal.

Install the project dependencies and run the API as usual:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m uvicorn neuralnotes.api:app --reload
```

The console exporter is for local development. An OTLP exporter and tracing
backend are not configured yet. Request and trace spans do not include query or
document text.
