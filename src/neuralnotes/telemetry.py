"""Local OpenTelemetry tracing setup for NeuralNotes."""

from collections import deque
from threading import Lock

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

_SAMPLE_LIMIT = 1_000
_generation_samples: deque[tuple[float, int | None, int | None]] = deque(
    maxlen=_SAMPLE_LIMIT
)
_samples_lock = Lock()


def record_generation(
    request_duration_ms: float,
    input_tokens: int | None,
    output_tokens: int | None,
) -> None:
    """Keep a bounded, process-local sample of model calls for summaries."""
    with _samples_lock:
        _generation_samples.append((request_duration_ms, input_tokens, output_tokens))


def generation_summary() -> dict[str, int | float | None]:
    """Summarize recent model latency and token usage without retaining content."""
    with _samples_lock:
        samples = tuple(_generation_samples)

    durations = sorted(sample[0] for sample in samples)
    input_values = [sample[1] for sample in samples if sample[1] is not None]
    output_values = [sample[2] for sample in samples if sample[2] is not None]

    def percentile(values: list[float], fraction: float) -> float | None:
        if not values:
            return None
        index = max(0, int(len(values) * fraction + 0.999999) - 1)
        return values[index]

    def average(values: list[int]) -> float | None:
        return sum(values) / len(values) if values else None

    return {
        "sample_count": len(samples),
        "sample_limit": _SAMPLE_LIMIT,
        "generation_latency_p50_ms": percentile(durations, 0.50),
        "generation_latency_p95_ms": percentile(durations, 0.95),
        "average_input_tokens": average(input_values),
        "average_output_tokens": average(output_values),
    }
