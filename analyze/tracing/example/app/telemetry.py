import logging
from contextvars import ContextVar

from fastapi import FastAPI, Request
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

request_id_var: ContextVar[str] = ContextVar('request_id', default='-')


class TraceContextFilter(logging.Filter):
    """Добавляет в каждую запись лога request_id, trace_id и span_id."""

    def filter(self, record: logging.LogRecord) -> bool:
        ctx = trace.get_current_span().get_span_context()
        record.trace_id = format(ctx.trace_id, '032x') if ctx.is_valid else '-'
        record.span_id = format(ctx.span_id, '016x') if ctx.is_valid else '-'
        record.request_id = request_id_var.get()
        return True


def setup_logging() -> None:
    handler = logging.StreamHandler()
    handler.addFilter(TraceContextFilter())
    handler.setFormatter(logging.Formatter(
        '%(levelname)s %(name)s request_id=%(request_id)s trace_id=%(trace_id)s span_id=%(span_id)s %(message)s'
    ))
    logging.basicConfig(level=logging.INFO, handlers=[handler])


def setup_tracing(app: FastAPI) -> None:
    # Имя сервиса и семплер SDK берёт из OTEL_SERVICE_NAME и OTEL_TRACES_SAMPLER*,
    # адрес Jaeger — из OTEL_EXPORTER_OTLP_ENDPOINT
    provider = TracerProvider()
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app, exclude_spans=['send', 'receive'])
    HTTPXClientInstrumentor().instrument()

    @app.middleware('http')
    async def remember_request_id(request: Request, call_next):
        request_id = request.headers.get('x-request-id', '-')
        trace.get_current_span().set_attribute('request_id', request_id)
        token = request_id_var.set(request_id)
        try:
            return await call_next(request)
        finally:
            request_id_var.reset(token)
