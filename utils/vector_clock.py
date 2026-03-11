import json

SERVICES = (
    "orchestrator",
    "transaction_verification",
    "fraud_detection",
    "suggestions",
)

VECTOR_CLOCK_METADATA_KEY = "x-vector-clock"
EVENT_TRACE_METADATA_KEY = "x-event-trace"
ORDER_ID_METADATA_KEY = "x-order-id"
SUGGESTED_BOOKS_METADATA_KEY = "x-suggested-books"


def new_clock():
    return {service: 0 for service in SERVICES}


def normalize_clock(clock):
    normalized = new_clock()
    if not clock:
        return normalized

    for service in SERVICES:
        normalized[service] = int(clock.get(service, 0))
    return normalized


def merge_clocks(*clocks):
    merged = new_clock()
    for clock in clocks:
        normalized = normalize_clock(clock)
        for service in SERVICES:
            merged[service] = max(merged[service], normalized[service])
    return merged


def tick(clock, service):
    updated = normalize_clock(clock)
    updated[service] += 1
    return updated


def serialize_clock(clock):
    return json.dumps(normalize_clock(clock), sort_keys=True)


def deserialize_clock(raw_clock):
    if not raw_clock:
        return new_clock()
    return normalize_clock(json.loads(raw_clock))


def serialize_trace(trace):
    return json.dumps(trace)


def deserialize_trace(raw_trace):
    if not raw_trace:
        return []
    return json.loads(raw_trace)


def record_event(trace, clock, service, event):
    event_clock = normalize_clock(clock)
    trace.append({"event": event, "service": service, "clock": event_clock})
    return trace


def metadata_to_dict(metadata):
    if not metadata:
        return {}
    return {key: value for key, value in metadata}
