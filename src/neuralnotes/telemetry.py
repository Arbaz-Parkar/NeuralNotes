"""Local OpenTelemetry tracing setup for NeuralNotes."""

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

from neuralnotes.settings import Settings

settings = Settings()
_provider = TracerProvider(resource=Resource.create({"service.name": "neuralnotes"}))
if settings.otel_exporter_endpoint:
    _exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_endpoint)
else:
    _exporter = ConsoleSpanExporter()
_provider.add_span_processor(SimpleSpanProcessor(_exporter))
trace.set_tracer_provider(_provider)

tracer = trace.get_tracer("neuralnotes")
