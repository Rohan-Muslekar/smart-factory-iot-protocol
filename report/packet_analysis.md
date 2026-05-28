# Module 1 Assignment: Packet Analysis
## Task 4: Wire-Level Protocol Annotation

> Hex values below are taken from live tshark captures (`captures/*.pcap`) of the running SmartFactory publisher, CoAP server, and AMQP producer.

---

## 4.2 MQTT Packet Annotations

### CONNECT Packet

```
Raw bytes (MQTT layer):
10 45  00 04 4D 51 54 54  04 2C 00 3C
00 1A 73 6D 61 72 74 66 61 63 74 6F 72 79 2D 70 75 62 6C 69 73 68 65 72 2D 30 30 31
00 14 66 61 63 74 6F 72 79 2F 6C 69 6E 65 31 2F 73 74 61 74 75 73
00 07 6F 66 66 6C 69 6E 65
```

| Field | Offset (bytes) | Raw Hex | Decoded Value |
|-------|---------------|---------|---------------|
| Frame type + flags (byte 1) | 0 | `10` | Type=CONNECT (0001), flags=0000 |
| Remaining length | 1 | `45` | 69 bytes |
| Protocol name length | 2-3 | `00 04` | 4 |
| Protocol name | 4-7 | `4D 51 54 54` | "MQTT" |
| Protocol version | 8 | `04` | 4 (MQTT 3.1.1) |
| Connect flags | 9 | `2C` | See breakdown below |
| Keep-alive | 10-11 | `00 3C` | 60 seconds |
| Client ID length | 12-13 | `00 1A` | 26 |
| Client ID | 14-39 | `73 6D 61 72 74 …` | "smartfactory-publisher-001" |
| Will topic length | 40-41 | `00 14` | 20 |
| Will topic | 42-61 | `66 61 63 74 6F 72 79 …` | "factory/line1/status" |
| Will message length | 62-63 | `00 07` | 7 |
| Will message | 64-70 | `6F 66 66 6C 69 6E 65` | "offline" |

**Connect Flags byte breakdown (0x2C = 0010 1100):**

| Bit | Name | Value | Meaning |
|-----|------|-------|---------|
| 7 | Username flag | 0 | No username |
| 6 | Password flag | 0 | No password |
| 5 | Will retain | 1 | LWT message is retained |
| 4-3 | Will QoS | 01 | LWT at QoS 1 |
| 2 | Will flag | 1 | LWT is configured |
| 1 | Clean session | 0 | Persistent session (clean_session=False) |
| 0 | Reserved | 0 | (reserved) |

---

### QoS 1 PUBLISH Packet

```
Raw bytes (MQTT layer):
32 A1 01  00 19 66 61 63 74 6F 72 79 2F 6C 69 6E 65 31 2F 74 65 6D 70 65 72 61 74 75 72 65
02 1F  7B 22 6C 69 6E 65 22 3A 20 22 6C 69 6E 65 31 22 2C …
```

| Field | Offset (bytes) | Raw Hex | Decoded Value |
|-------|---------------|---------|---------------|
| Fixed header byte 1 | 0 | `32` | Type=PUBLISH(0011), DUP=0, QoS=01, RETAIN=0 |
| Remaining length | 1-2 | `A1 01` | 161 bytes (variable-length encoding) |
| Topic length | 3-4 | `00 19` | 25 |
| Topic string | 5-29 | `66 61 63 74 6F 72 79 2F 6C 69 6E 65 31 …` | "factory/line1/temperature" |
| Packet Identifier | 30-31 | `02 1F` | 543 |
| Payload | 32-… | `7B 22 6C 69 6E 65 …` | `{"line": "line1", "sensor": "temperature", "value": 68.985, ...}` |

**Fixed header byte 1 bit expansion (0x32 = 0011 0010):**

| Bits 7-4 (packet type) | Bit 3 (DUP) | Bits 2-1 (QoS) | Bit 0 (RETAIN) |
|------------------------|-------------|----------------|----------------|
| `0011` = PUBLISH (3)  | `0` = No duplicate | `01` = QoS 1 | `0` = Not retained |

---

### PUBACK Packet

```
Raw bytes (MQTT layer):  40 02 02 1F
```

| Field | Offset | Raw Hex | Decoded Value |
|-------|--------|---------|---------------|
| Fixed header | 0 | `40` | Type=PUBACK (0100) |
| Remaining length | 1 | `02` | 2 bytes |
| Packet Identifier | 2-3 | `02 1F` | 543 |

**Packet Identifier match:** PUBLISH PKT ID = 543 ; PUBACK PKT ID = 543 ; **Match? Yes**

---

## 4.3 CoAP Packet Annotations

### CON GET Request

```
Raw bytes (UDP payload):
42 01 69 45  BD BE  39 6C 6F 63 61 6C 68 6F 73 74
87 66 61 63 74 6F 72 79  05 6C 69 6E 65 31  0B 74 65 6D 70 65 72 61 74 75 72 65
[Header+Token] [Uri-Host] [--------- Uri-Path segments ----------]
```

| Field | Bits/Bytes | Raw Value | Decoded Value |
|-------|-----------|-----------|---------------|
| Version (bits 7-6) | 2 bits | `01` | 1 (always 1) |
| Type (bits 5-4) | 2 bits | `00` | 0 = CON |
| TKL (bits 3-0) | 4 bits | `0010` | Token length = 2 |
| Code (byte 1) | 8 bits | `01` | 0.01 = GET |
| Message ID (bytes 2-3) | 16 bits | `69 45` | 26949 |
| Token (bytes 4-5) | 2 bytes | `BD BE` | 0xBDBE |
| Option Delta | 4 bits | `3` | Delta = 3, Option# = 3 (Uri-Host) |
| Option Length | 4 bits | `9` | 9 bytes |
| Option Value | 9 bytes | `6C 6F 63 61 6C 68 6F 73 74` | "localhost" |
| Option Delta | 4 bits | `8` | Delta = 8, Option# = 3+8 = 11 (Uri-Path) |
| Option Length | 4 bits | `7` | 7 bytes |
| Option Value | 7 bytes | `66 61 63 74 6F 72 79` | "factory" (Uri-Path segment 1) |
| Option Delta | 4 bits | `0` | Delta = 0, Option# = 11 (Uri-Path) |
| Option Length | 4 bits | `5` | 5 bytes |
| Option Value | 5 bytes | `6C 69 6E 65 31` | "line1" (Uri-Path segment 2) |
| Option Delta | 4 bits | `0` | Delta = 0, Option# = 11 (Uri-Path) |
| Option Length | 4 bits | `B` (11) | 11 bytes |
| Option Value | 11 bytes | `74 65 6D 70 65 72 61 74 75 72 65` | "temperature" (Uri-Path segment 3) |

**Byte 0 full expansion (0x42):**

| Bit 7 | Bit 6 | Bit 5 | Bit 4 | Bit 3 | Bit 2 | Bit 1 | Bit 0 |
|-------|-------|-------|-------|-------|-------|-------|-------|
| Ver   | Ver   | T     | T     | TKL   | TKL   | TKL   | TKL   |
| `0`   | `1`   | `0`   | `0`   | `0`   | `0`   | `1`   | `0`   |

---

### ACK 2.05 Content Response

```
Raw bytes (UDP payload):
62 45 69 45  BD BE  C1 32  FF  7B 22 76 61 6C 75 65 …
[Header+Token] [Opt] [PM] [--- JSON payload ---]
```

| Field | Bytes | Raw Hex | Decoded Value |
|-------|-------|---------|---------------|
| Fixed header byte 0 | 0 | `62` | Ver=01, T=10 (ACK), TKL=0010 (2) |
| Code byte 1 | 1 | `45` | 2.05 = Content |
| Message ID | 2-3 | `69 45` | 26949 (matches request? **Yes**) |
| Token | 4-5 | `BD BE` | 0xBDBE (matches request? **Yes**) |
| Option: Content-Format | 6-7 | `C1 32` | Option# = 12 (delta=12, len=1), Value = 0x32 = 50 (application/json) |
| Payload Marker | 8 | `FF` | 0xFF |
| Payload | 9-… | `7B 22 76 61 6C …` | `{"value": 71.028, "unit": "C", "ts": "2026-05-27T21:31:22..."}` |

---

### Observe Notification

| Field | Value |
|-------|-------|
| Observe option number | 6 |
| Observe sequence value | Incrementing integer (e.g., 1, 2, 3…) |
| Message type | NON (non-confirmable, for efficiency) |
| Response code | 2.05 Content |

---

## 4.4 AMQP Frame Annotations

### basic.publish Method Frame

```
Raw bytes (AMQP frame):
01 00 01  00 00 00 2F  00 3C 00 28  00 00
0D 69 6F 74 2E 74 65 6C 65 6D 65 74 72 79
19 66 61 63 74 6F 72 79 2E 6C 69 6E 65 31 2E 74 65 6D 70 65 72 61 74 75 72 65
01  CE
```

| Field | Bytes | Raw Hex | Decoded Value |
|-------|-------|---------|---------------|
| Frame Type | 0 | `01` | 1 = Method |
| Channel | 1-2 | `00 01` | 1 |
| Payload Size | 3-6 | `00 00 00 2F` | 47 bytes |
| Class ID | 7-8 | `00 3C` | 60 = basic |
| Method ID | 9-10 | `00 28` | 40 = basic.publish |
| Reserved (ticket) | 11-12 | `00 00` | (unused) |
| Exchange name length | 13 | `0D` | 13 |
| Exchange name | 14-26 | `69 6F 74 2E 74 65 6C 65 6D 65 74 72 79` | "iot.telemetry" |
| Routing key length | 27 | `19` | 25 |
| Routing key | 28-52 | `66 61 63 74 6F 72 79 2E 6C 69 6E 65 31 …` | "factory.line1.temperature" |
| Mandatory + Immediate | 53 | `01` | mandatory=1, immediate=0 |
| Frame End | 54 | `CE` | 0xCE |

---

### Content Header Frame

```
Raw bytes (AMQP frame):
02 00 01  00 00 00 2E  00 3C 00 00
00 00 00 00 00 00 00 85  91 40
10 61 70 70 6C 69 63 61 74 69 6F 6E 2F 6A 73 6F 6E
02  05 36 30 30 30 30  00 00 00 00 6A 17 61 94  CE
```

| Field | Bytes | Raw Hex | Decoded Value |
|-------|-------|---------|---------------|
| Frame Type | 0 | `02` | 2 = Header |
| Channel | 1-2 | `00 01` | 1 |
| Payload Size | 3-6 | `00 00 00 2E` | 46 bytes |
| Class ID | 7-8 | `00 3C` | 60 = basic |
| Weight | 9-10 | `00 00` | (unused) |
| Body Size | 11-18 | `00 00 00 00 00 00 00 85` | 133 bytes |
| Property Flags | 19-20 | `91 40` | bits set: content_type, delivery_mode, expiration, timestamp |
| content_type length | 21 | `10` | 16 |
| content_type | 22-37 | `61 70 70 6C 69 63 61 74 69 6F 6E 2F 6A 73 6F 6E` | "application/json" |
| delivery_mode | 38 | `02` | 2 (persistent) |
| expiration length | 39 | `05` | 5 |
| expiration | 40-44 | `36 30 30 30 30` | "60000" |
| timestamp | 45-52 | `00 00 00 00 6A 17 61 94` | 1780302228 (Unix epoch) |
| Frame End | last | `CE` | 0xCE |

---

### Heartbeat Frame

```
Raw bytes (AMQP frame):  08 00 00  00 00 00 00  CE
```

| Field | Value |
|-------|-------|
| Frame Type | `08` (8 = Heartbeat) |
| Channel | `00 00` (always channel 0) |
| Payload Size | `00 00 00 00` (0 bytes) |
| Payload | _(empty)_ |
| Frame End | `CE` |

**Why is the Heartbeat payload empty?**

> Heartbeat frames serve purely as keep-alive signals to confirm that the TCP connection is still active and both peers are responsive. They carry no application data; their sole purpose is presence detection. The AMQP 0-9-1 specification mandates that heartbeat frames must have a zero-length payload and must always be sent on channel 0, since they are a connection-level mechanism rather than a channel-level one.

---

*Module 1 Assignment, Real-Time Data Analytics for IoT*
