import os
import functools
import logging
from typing import Any, Callable
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_tracing(service_name: str = "araya-research-engine"):
    """Configures OpenTelemetry tracing."""
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    
    # Export to Console for local debugging
    console_exporter = ConsoleSpanExporter()
    provider.add_span_processor(BatchSpanProcessor(console_exporter))
    
    # Export to LangSmith/Honeycomb/etc if endpoint is provided
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        logger.info(f"OTLP Exporting enabled to {otlp_endpoint}")

    trace.set_tracer_provider(provider)
    return trace.get_tracer(service_name)

tracer = setup_tracing()

def instrument_node(phase: str):
    """
    Decorator to instrument LangGraph nodes with OpenTelemetry spans.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(state: Any, *args, **kwargs):
            # Extract research_id from state if available
            research_id = state.get("research_id", "unknown")
            
            with tracer.start_as_current_span(
                f"agent_phase.{phase}",
                attributes={
                    "phase": phase,
                    "research_id": research_id,
                    "func_name": func.__name__
                }
            ) as span:
                try:
                    result = await func(state, *args, **kwargs)
                    span.set_attribute("status", "success")
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(trace.Status(trace.StatusCode.ERROR))
                    logger.error(f"Error in phase {phase}: {e}")
                    raise e
        return wrapper
    return decorator
