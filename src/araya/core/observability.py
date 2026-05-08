import os
import functools
import logging
import uuid
import time
from typing import Any, Callable, Dict
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

# Set up logging with structured format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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
    Decorator to instrument LangGraph nodes with OpenTelemetry spans and structured logging.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(state: Any, *args, **kwargs):
            # Generate or extract request ID for tracing
            request_id = state.get("request_id") or str(uuid.uuid4())
            
            # Extract research_id from state if available
            research_id = state.get("research_id", "unknown")
            
            # Start timing
            start_time = time.time()
            
            # Structured logging for entry
            logger.info(
                f"Starting agent phase: {phase}",
                extra={
                    "request_id": request_id,
                    "research_id": research_id,
                    "phase": phase,
                    "func_name": func.__name__,
                    "event": "phase_start"
                }
            )
            
            with tracer.start_as_current_span(
                f"agent_phase.{phase}",
                attributes={
                    "phase": phase,
                    "research_id": research_id,
                    "request_id": request_id,
                    "func_name": func.__name__
                }
            ) as span:
                try:
                    result = await func(state, *args, **kwargs)
                    
                    # Calculate duration
                    duration_ms = (time.time() - start_time) * 1000
                    
                    # Set span attributes
                    span.set_attribute("status", "success")
                    span.set_attribute("duration_ms", duration_ms)
                    
                    # Structured logging for success
                    logger.info(
                        f"Completed agent phase: {phase}",
                        extra={
                            "request_id": request_id,
                            "research_id": research_id,
                            "phase": phase,
                            "func_name": func.__name__,
                            "duration_ms": duration_ms,
                            "event": "phase_end",
                            "status": "success"
                        }
                    )
                    
                    return result
                except Exception as e:
                    # Calculate duration
                    duration_ms = (time.time() - start_time) * 1000
                    
                    # Set span attributes for error
                    span.record_exception(e)
                    span.set_status(trace.Status(trace.StatusCode.ERROR))
                    span.set_attribute("duration_ms", duration_ms)
                    span.set_attribute("error.message", str(e))
                    
                    # Structured logging for error
                    logger.error(
                        f"Error in agent phase {phase}: {e}",
                        extra={
                            "request_id": request_id,
                            "research_id": research_id,
                            "phase": phase,
                            "func_name": func.__name__,
                            "duration_ms": duration_ms,
                            "event": "phase_end",
                            "status": "error",
                            "error_type": type(e).__name__,
                            "error_message": str(e)
                        }
                    )
                    raise e
        return wrapper
    return decorator

# Helper function to add request ID to state
def add_request_id(state: Dict[str, Any]) -> Dict[str, Any]:
    """Add a request ID to the state if not present."""
    if "request_id" not in state:
        state["request_id"] = str(uuid.uuid4())
    return state
