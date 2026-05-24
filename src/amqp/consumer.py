"""
Module 1 Assignment — Task 3.3
AMQP Consumer with Manual ACK and DLX Inspection

Complete all TODO sections.
"""

import json
import logging
import random
import time
from datetime import datetime, timezone

import pika
import pika.exceptions

from src.amqp.topology import (
    QUEUE_ALL, QUEUE_DLX,
    EXCHANGE_TELEMETRY, EXCHANGE_DLX,
    get_connection_params
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")
log = logging.getLogger(__name__)

PREFETCH_COUNT   = 5
FAILURE_RATE     = 0.10          # 10% random processing failures
DLX_POLL_EVERY   = 30            # seconds between DLX queue polls


class SmartFactoryConsumer:

    def __init__(self):
        self._connection    = None
        self._channel       = None
        self._processed     = 0
        self._failed        = 0
        self._alerts_seen   = 0
        self._last_dlx_poll = time.time()

    # ── Connection ─────────────────────────────────────────────────────────────

    def connect(self) -> None:
        """
        TODO 1: Connect to RabbitMQ.
        Requirements:
          - Use get_connection_params()
          - Open a channel
          - Set QoS: prefetch_count = PREFETCH_COUNT, global=False
          - Register on_message as the callback for QUEUE_ALL
            with auto_ack=False
        """
        params = get_connection_params()
        self._connection = pika.BlockingConnection(params)
        self._channel = self._connection.channel()
        self._channel.basic_qos(prefetch_count=PREFETCH_COUNT)
        self._channel.basic_consume(
            queue=QUEUE_ALL,
            on_message_callback=self.on_message,
            auto_ack=False,
        )

    # ── Message Handler ────────────────────────────────────────────────────────

    def on_message(
        self,
        channel: pika.adapters.blocking_connection.BlockingChannel,
        method:  pika.spec.Basic.Deliver,
        props:   pika.spec.BasicProperties,
        body:    bytes,
    ) -> None:
        """
        TODO 2: Main message handler.
        Requirements:
          1. Parse body as JSON (handle decode errors → NACK requeue=False)
          2. Check if routing key ends with ".critical":
               - Print formatted CRITICAL ALERT (line, value, timestamp)
               - Increment self._alerts_seen
               - ACK the message
               - Return early
          3. Simulate processing failure with probability FAILURE_RATE:
               - If failure: NACK with requeue=False (routes to DLX)
                 Log: "NACK (simulated failure) tag={tag} key={routing_key}"
                 Increment self._failed
               - If success: ACK the message
                 Log: "[PROCESSED] {routing_key}  val={value}  tag={tag}"
                 Increment self._processed
          4. Every DLX_POLL_EVERY seconds, call _poll_dlx()
        """
        tag = method.delivery_tag
        routing_key = method.routing_key

        try:
            payload = json.loads(body)
        except (json.JSONDecodeError, TypeError):
            log.warning("Invalid JSON, NACKing tag=%d", tag)
            channel.basic_nack(delivery_tag=tag, requeue=False)
            self._failed += 1
            return

        if routing_key.endswith(".critical"):
            self._print_critical_alert(routing_key, payload)
            self._alerts_seen += 1
            channel.basic_ack(delivery_tag=tag)
            return

        if random.random() < FAILURE_RATE:
            channel.basic_nack(delivery_tag=tag, requeue=False)
            log.info("NACK (simulated failure) tag=%d key=%s", tag, routing_key)
            self._failed += 1
        else:
            channel.basic_ack(delivery_tag=tag)
            log.info("[PROCESSED] %s  val=%s  tag=%d",
                     routing_key, payload.get("value", "?"), tag)
            self._processed += 1

        if time.time() - self._last_dlx_poll >= DLX_POLL_EVERY:
            self._poll_dlx()

    def _print_critical_alert(self, routing_key: str, payload: dict) -> None:
        """
        TODO 3: Print a formatted critical temperature alert.
        Format:
          ╔══════════════════════════════════════╗
          ║  ⚠ CRITICAL ALERT — {routing_key}
          ║  Temperature: {value}°C
          ║  Timestamp:   {timestamp}
          ╚══════════════════════════════════════╝
        """
        print("╔══════════════════════════════════════╗")
        print(f"║  ⚠ CRITICAL ALERT — {routing_key}")
        print(f"║  Temperature: {payload.get('value', '?')}°C")
        print(f"║  Timestamp:   {payload.get('timestamp', '?')}")
        print("╚══════════════════════════════════════╝")

    # ── DLX Inspector ─────────────────────────────────────────────────────────

    def _poll_dlx(self) -> None:
        """
        TODO 4: Drain and inspect all messages currently in QUEUE_DLX.
        Requirements:
          - Use channel.basic_get(QUEUE_DLX, auto_ack=True) in a loop
            until it returns (None, None, None)
          - For each dead-lettered message:
              * Parse body as JSON
              * Extract x-death header from properties.headers
              * Print:
                  [DEAD LETTER] routing_key={key}
                    Original queue: {x-death[0]["queue"]}
                    Death reason:   {x-death[0]["reason"]}
                    Death count:    {x-death[0]["count"]}
                    Value:          {payload.get("value", "?")}
          - Log: "DLX poll complete — {n} dead-lettered messages inspected"
        Note: basic_get is synchronous — this is safe to call from on_message
              since we're in the same thread.
        """
        count = 0
        while True:
            method, props, body = self._channel.basic_get(QUEUE_DLX, auto_ack=True)
            if method is None:
                break
            count += 1
            try:
                payload = json.loads(body)
            except (json.JSONDecodeError, TypeError):
                payload = {}
            x_death = []
            if props.headers and "x-death" in props.headers:
                x_death = props.headers["x-death"]
            print(f"[DEAD LETTER] routing_key={method.routing_key}")
            if x_death:
                d = x_death[0]
                print(f"  Original queue: {d.get('queue', '?')}")
                print(f"  Death reason:   {d.get('reason', '?')}")
                print(f"  Death count:    {d.get('count', '?')}")
            print(f"  Value:          {payload.get('value', '?')}")
        log.info("DLX poll complete — %d dead-lettered messages inspected", count)
        self._last_dlx_poll = time.time()

    # ── Run ────────────────────────────────────────────────────────────────────

    def run(self) -> None:
        self.connect()
        log.info("Consumer ready. Consuming from %s (prefetch=%d)", QUEUE_ALL, PREFETCH_COUNT)
        try:
            self._channel.start_consuming()
        except KeyboardInterrupt:
            self._channel.stop_consuming()
        finally:
            if self._connection and not self._connection.is_closed:
                self._connection.close()
            log.info("Final stats — processed: %d  failed(DLX): %d  alerts: %d",
                     self._processed, self._failed, self._alerts_seen)


if __name__ == "__main__":
    consumer = SmartFactoryConsumer()
    consumer.run()
