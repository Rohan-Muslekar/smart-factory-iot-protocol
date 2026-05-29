# SmartFactory IoT Protocol Integration

**Course:** Real-Time Data Analytics for IoT, Module 2 (Foundations)
**Student:** Rohan Muslekar (101006689)
**Date:** 2026-05-28

---

## Overview

Multi-protocol IoT data pipeline for SmartFactory Inc., connecting sensor telemetry from two production lines to a backend broker using MQTT, CoAP, and AMQP. Includes wire-level packet analysis and a protocol comparison report.

---

## Reports

- [Packet Analysis (Task 4)](report/packet_analysis.md) - Wire-level annotations of MQTT, CoAP, and AMQP packets from live tshark captures
- [Protocol Comparison Report (Task 5)](report/comparison_report.md) - QoS comparison, CoAP-HTTP proxy mapping, protocol recommendations, and reflection

---

## Prerequisites

- Python 3.10+
- Docker & Docker Compose
- Wireshark / tshark (for packet captures)

## Quick Start

```bash
# 1. Create virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Start infrastructure (Mosquitto + RabbitMQ)
docker compose up -d

# 3. Run all tests (34 total)
pytest tests/ -v --tb=short
```

## Running Individual Components

```bash
# MQTT
python -m src.mqtt.publisher       # Terminal 1
python -m src.mqtt.subscriber      # Terminal 2

# CoAP
python -m src.coap.server          # Terminal 1
python -m src.coap.observer        # Terminal 2

# AMQP (run topology first)
python -m src.amqp.topology        # Once: sets up RabbitMQ exchanges/queues
python -m src.amqp.producer        # Terminal 1
python -m src.amqp.consumer        # Terminal 2
```

## Running Tests

```bash
pytest tests/ -v                            # All tests
pytest tests/mqtt/ -v                       # MQTT tests (12)
pytest tests/coap/ -v                       # CoAP tests (14)
pytest tests/amqp/ -v                       # AMQP tests (8)
pytest tests/mqtt/test_qos_loss.py -v -s    # QoS experiment with output table
```

## Infrastructure

| Service | Port | URL |
|---------|------|-----|
| Mosquitto MQTT | 1883 | `mqtt://localhost:1883` |
| RabbitMQ AMQP | 5672 | `amqp://localhost:5672` |
| RabbitMQ Management | 15672 | http://localhost:15672 (guest/guest) |
| CoAP Server | 5683 | `coap://localhost:5683` |

```bash
docker compose up -d      # Start services
docker compose down        # Stop services
```

## Repository Structure

```
├── src/
│   ├── mqtt/
│   │   ├── publisher.py        ← Task 1.1: Multi-sensor MQTT publisher
│   │   └── subscriber.py       ← Task 1.2: Wildcard subscriber with alerts
│   ├── coap/
│   │   ├── server.py           ← Task 2.1: Observable resources + Block2 manifest
│   │   └── observer.py         ← Task 2.2: Concurrent observer + stale detection
│   └── amqp/
│       ├── topology.py         ← Task 3.1: Exchange/queue/binding declarations
│       ├── producer.py         ← Task 3.2: Publisher with confirms + critical routing
│       └── consumer.py         ← Task 3.3: Consumer with NACK + DLX polling
├── report/
│   ├── packet_analysis.md      ← Task 4: Wire-level protocol annotations
│   └── comparison_report.md    ← Task 5: Protocol comparison report
├── captures/                   ← Packet captures (git-ignored)
├── tests/                      ← Pre-written test suite (do not modify)
└── docker-compose.yml
```
