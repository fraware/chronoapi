from prometheus_client import Counter, Histogram

forecast_requests_total = Counter(
    "forecast_requests_total",
    "Total number of forecast requests processed",
    ["method", "endpoint"],
)
forecast_latency_seconds = Histogram(
    "forecast_latency_seconds",
    "Time taken to process forecast requests",
    ["method", "endpoint"],
)
kafka_messages_total = Counter(
    "kafka_messages_total",
    "Total number of Kafka messages processed",
    ["status"],
)
http_requests_total = Counter(
    "http_requests_total",
    "HTTP responses by method, route template, and status class",
    ["method", "path_template", "status_class"],
)
