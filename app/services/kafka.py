from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from app.config import settings
from app.observability.metrics import kafka_messages_total
from app.services.forecast import run_forecast

if TYPE_CHECKING:
    import torch

logger = logging.getLogger("forecasting_service")


async def kafka_consumer_loop(forecast_model: torch.nn.Module) -> None:
    consumer = AIOKafkaConsumer(
        settings.kafka_input_topic,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id="forecasting_service_group",
    )
    producer = AIOKafkaProducer(bootstrap_servers=settings.kafka_bootstrap_servers)
    await consumer.start()
    await producer.start()
    try:
        async for msg in consumer:
            try:
                kafka_messages_total.labels(status="received").inc()
                logger.info(
                    "Received Kafka message",
                    extra={
                        "extra_payload": {
                            "topic": msg.topic,
                            "partition": msg.partition,
                            "offset": msg.offset,
                        }
                    },
                )
                request_data = json.loads(msg.value.decode("utf-8"))
                forecast_result = run_forecast(request_data, forecast_model)
                response = {
                    "forecast": forecast_result,
                    "request_id": request_data.get("request_id"),
                }
                await producer.send_and_wait(
                    settings.kafka_output_topic, json.dumps(response).encode("utf-8")
                )
                kafka_messages_total.labels(status="processed").inc()
                logger.info(
                    "Sent forecast result to Kafka output topic",
                    extra={"extra_payload": {"request_id": request_data.get("request_id")}},
                )
            except Exception:
                kafka_messages_total.labels(status="error").inc()
                logger.exception("Error processing Kafka message")
    finally:
        await consumer.stop()
        await producer.stop()


async def run_kafka_consumer(forecast_model: torch.nn.Module) -> None:
    backoff = 1.0
    max_backoff = 60.0
    while True:
        try:
            await kafka_consumer_loop(forecast_model)
            break
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception(
                "Kafka consumer crashed; retrying",
                extra={"extra_payload": {"backoff_s": backoff}},
            )
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, max_backoff)
