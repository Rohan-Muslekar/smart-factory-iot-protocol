# Module 1 Assignment: Protocol Comparison Report

**Student Name:** Rohan Muslekar
**Student ID:**   101006689
**Date:**         2026-05-25

---

## 5.1 QoS Comparison Results Table

| Protocol / QoS | Sent | Received | Lost (%) | Duplicates | Avg Latency (ms) |
|----------------|------|----------|----------|------------|-----------------|
| MQTT QoS 0 | 100 | 91 | 9.0% | 0 | 1.2 |
| MQTT QoS 1 | 100 | 100 | 0.0% | 3 | 3.4 |
| MQTT QoS 2 | 100 | 100 | 0.0% | 0 | 5.2 |
| CoAP NON | 100 | 88 | 12.0% | 0 | 0.9 |
| CoAP CON | 100 | 100 | 0.0% | 2 | 4.1 |
| AMQP (publisher confirms) | 100 | 100 | 0.0% | 0 | 3.8 |

> **Methodology:** 100 messages published per QoS level. MQTT measurements collected by `test_qos_loss.py`, which uses application-level loss simulation (randomly dropping ~10% of in-flight messages before broker acknowledgement) to isolate QoS-level behavior from TCP's transport reliability. CoAP NON/CON tested with a similar 100-message experiment over UDP with `tc netem loss 10%` on the loopback interface, since UDP has no built-in retransmission. AMQP runs over TCP and uses publisher confirms for application-level delivery guarantees; the table reflects confirm-mode delivery with no simulated loss.

**Analysis Questions:**

1. **Why does QoS 0 lose messages while QoS 1 and 2 do not?** *(2-3 sentences)*

   > As the table shows, QoS 0 lost 9 out of 100 messages (9.0%) while QoS 1 and QoS 2 both delivered all 100. QoS 0 uses a "fire and forget" model where the publisher sends the PUBLISH packet once with no acknowledgement or retransmission; when a packet is dropped, neither side is aware of the loss and the message is gone. QoS 1 and QoS 2 implement acknowledgement-and-retry mechanisms (PUBACK for QoS 1, a four-step PUBREC/PUBREL/PUBCOMP handshake for QoS 2) that detect missing packets and retransmit until delivery is confirmed, which is why both show 0% loss even under 10% simulated packet loss.

2. **QoS 1 may show duplicates. Under what circumstances does this happen, and is it a problem for sensor telemetry?** *(2-3 sentences)*

   > The table shows QoS 1 produced 3 duplicate messages out of 100. Duplicates occur when the broker successfully receives and stores a PUBLISH but the corresponding PUBACK is lost on the return path; the publisher, having not received confirmation, retransmits the same message with the DUP flag set, causing the broker to deliver it a second time. For sensor telemetry this is generally acceptable because downstream consumers can deduplicate using the sequence number or timestamp embedded in the payload, and receiving a redundant temperature reading is far less harmful than missing a critical spike above the 85C threshold.

3. **QoS 2 has higher latency than QoS 1. What causes this, and when is the trade-off worth it?** *(2-3 sentences)*

   > The table confirms this: QoS 2 averaged 5.2 ms per message compared to 3.4 ms for QoS 1, roughly 53% higher. QoS 2 requires a four-packet handshake (PUBLISH > PUBREC > PUBREL > PUBCOMP) versus QoS 1's two-packet exchange (PUBLISH > PUBACK), adding two extra network round trips per message, and under packet loss each step may need retransmission. The trade-off is worth it when exactly-once semantics are critical, such as actuator commands where a duplicate "activate cooling fan" could cause motor oscillation, or billing events where duplicates would produce incorrect charges.

---

## 5.2 CoAP-HTTP Proxy Mapping

| HTTP Header | CoAP Option | Your Observed Value |
|-------------|-------------|---------------------|
| Content-Type | Content-Format (Option 12) | 50 (application/json) |
| Cache-Control: max-age | Max-Age (Option 14) | Not set (defaults to 60s per RFC 7252) |
| ETag | ETag (Option 4) | Not set |
| Location | Location-Path (Option 8) | Not set (no resource creation via POST) |

---

## 5.3 Protocol Selection Recommendation

### Data Path Recommendations

| Data Path | Recommended Protocol | Justification |
|-----------|---------------------|---------------|
| Sensor to Cloud (high frequency, <100 ms latency) | MQTT with QoS 1 | Low per-message overhead, persistent TCP, at-least-once delivery |
| Actuator commands (safety-critical, exactly-once) | MQTT QoS 2 | Four-step handshake guarantees exactly-once delivery |
| Backend service-to-service routing | AMQP | Topic exchanges, dead letter queues, and flexible routing topologies |
| OTA firmware delivery to constrained MCU (Class 2) | CoAP with Block2 | Block-wise transfer designed for constrained devices, UDP minimizes memory |

### Detailed Justification

For the **Sensor to Cloud** data path requiring high-frequency telemetry with sub-100 ms latency, MQTT with QoS 1 is the strongest choice. During implementation, MQTT's persistent TCP connection proved highly efficient for continuous sensor streams. Once the initial TCP handshake and MQTT CONNECT are complete, each subsequent PUBLISH carries minimal protocol overhead. Examining the wire-level MQTT PUBLISH packets in Task 4 revealed a fixed header of just 2 bytes (message type plus remaining length) followed by the topic string and payload, with no per-message framing beyond what TCP provides. QoS 1 adds only a 2-byte Packet Identifier and a small PUBACK response, keeping the overhead under 10 bytes per message while guaranteeing at-least-once delivery. The QoS comparison experiment in Section 5.1 confirmed that QoS 1 delivered all 100 test messages at an average latency of 3.4 ms, well within the 100 ms target, while QoS 0 lost 9% of messages under 10% simulated packet loss due to its lack of acknowledgement.

For **actuator commands** that are safety-critical and require exactly-once semantics, MQTT QoS 2 is the appropriate choice despite its higher latency. The four-step handshake (PUBLISH > PUBREC > PUBREL > PUBCOMP) ensures that a cooling fan command is executed precisely once: not lost (which could cause overheating) and not duplicated (which could cause rapid on/off oscillation damaging the fan motor). The 5.2 ms average latency observed in the QoS experiment (Section 5.1) is acceptable for actuator commands since they are infrequent (triggered only when temperature exceeds the 85C threshold) and correctness outweighs speed. CoAP's CON (confirmable) messages were considered but the comparison table shows CON produced 2 duplicates out of 100 messages, confirming it only provides at-least-once delivery without duplicate suppression at the protocol level, making MQTT QoS 2 the safer option for safety-critical control.

For **backend service-to-service routing**, AMQP via RabbitMQ is the clear recommendation. The implementation of the AMQP topology in Task 3 demonstrated capabilities that neither MQTT nor CoAP can match for internal routing: topic exchanges with flexible binding patterns (e.g., `factory.line1.#` to route all line1 data to a dedicated queue, `#.critical` to fan out critical alerts), dead letter exchanges that automatically capture failed or expired messages for inspection, message TTL policies that prevent queue buildup from stale data, and per-queue maximum lengths with configurable overflow behavior. The publisher confirms mechanism provides end-to-end delivery guarantees from producer to broker, and manual ACK/NACK on the consumer side allows fine-grained control over message processing, including the ability to reject and dead-letter messages that fail processing. The packet capture analysis showed that AMQP's three-frame structure (Method + Content Header + Body) carries more overhead per message than MQTT, but this is irrelevant for backend communication where network bandwidth is plentiful and the routing flexibility is far more valuable.

For **OTA firmware delivery to constrained MCUs** (Class 2 devices with ~50 KB RAM), CoAP with Block2 transfer is the ideal protocol. The implementation of the `/factory/manifest` resource in Task 2 demonstrated CoAP's Block2 mechanism, which automatically fragments large payloads into individually confirmable blocks that fit within constrained device memory. Unlike MQTT or AMQP, which require a full TCP stack (typically 10-20 KB of RAM), CoAP runs over UDP and can operate with a minimal network stack suitable for Class 2 devices. The QoS comparison in Section 5.1 also shows CoAP NON achieved the lowest per-message latency (0.9 ms) of any protocol tested, confirming its suitability for constrained devices where low overhead matters more than guaranteed delivery. The CoAP packet analysis in Task 4 confirmed the compact 4-byte fixed header with efficient option delta encoding, and the Block2 transfer successfully reassembled the 3+ KB manifest from multiple blocks without requiring the client to buffer the entire payload. CoAP's built-in content negotiation and proxy support also enable firmware distribution through intermediary caches, reducing load on the origin server during fleet-wide updates.

---

## 5.4 Reflection

### Technical Challenge

The most significant technical challenge I encountered was implementing CoAP's Observe pattern with concurrent subscriptions and stale notification detection. The observer client needed to simultaneously monitor temperature resources on both production lines using `asyncio.gather`, which required careful coordination between the observation loops and the 60-second cancellation timer. The stale notification detection added further complexity. The CoAP Observe specification uses a 24-bit sequence number that can wrap around, so a simple "is the new sequence less than the old one?" check would incorrectly flag valid notifications after a wrap-around event. I resolved this by implementing the RFC 7641 freshness check: a notification is considered stale only if its sequence number is lower than the last received AND the difference is less than 2^23 (half the sequence space), which correctly handles wrap-around. Getting the `asyncio.wait_for` timeout to cleanly cancel both observation streams without leaving dangling tasks required explicitly cancelling the observation protocol request in a `finally` block.

### Most Surprising Protocol Difference

The most surprising difference observed during packet capture was the dramatic variation in per-message overhead across protocols. An MQTT PUBLISH for a simple temperature reading (approximately 80 bytes of JSON payload) required only about 6-8 bytes of protocol framing: the 2-byte fixed header, a 2-byte topic length prefix, and the topic string itself. The equivalent CoAP response was similarly compact at roughly 12 bytes of header and options. However, the AMQP equivalent required three separate frames: a Method frame (basic.publish with exchange and routing key), a Content Header frame (with property flags, delivery_mode, content_type, and expiration), and a Body frame, each with its own frame type byte, channel number, payload size, and frame-end marker (0xCE). The total AMQP framing overhead exceeded 100 bytes, more than the payload itself. This made concrete what textbooks describe abstractly: AMQP's rich feature set (delivery modes, message properties, mandatory flags) comes at a measurable wire-level cost.

### Most Complex Protocol to Implement

CoAP was the most complex protocol to implement. Unlike MQTT, where the paho-mqtt library and Mosquitto broker handle connection management, topic routing, and session persistence, CoAP required building the resource tree manually using aiocoap's `Resource` and `Site` classes, with each sensor endpoint implementing its own `render_get` coroutine and the actuator endpoint implementing `render_put` with input validation and correct response codes (2.05 Content, 2.04 Changed, 4.00 Bad Request). The Block2 transfer for the `/factory/manifest` resource required constructing a payload larger than 1024 bytes and relying on aiocoap's internal block-wise fragmentation, which was difficult to verify because reassembly happens transparently on the client side and any misconfiguration produces a truncated response with no error. Content-Format option codes (e.g., 50 for application/json) had to be set explicitly on every response, unlike MQTT where the payload is opaque bytes and the subscriber interprets them. The HTTP-to-CoAP proxy added another layer of complexity: translating HTTP headers to CoAP options (Content-Type to Content-Format, Cache-Control to Max-Age) required understanding both protocol stacks and running an aiohttp server alongside the CoAP context within the same asyncio event loop. Debugging was also harder than MQTT since CoAP runs over UDP with no session state, so errors like a wrong token length or malformed option delta produced silent failures rather than connection-level exceptions.

---

*Module 1 Assignment, Real-Time Data Analytics for IoT*
