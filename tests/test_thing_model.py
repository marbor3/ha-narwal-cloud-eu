"""Tests for the ODM thing-model support (Freo S / YJCC032)."""

from __future__ import annotations

import asyncio
import json

import sys

from test_coordinator import COORDINATOR


def _coordinator_module():
    return COORDINATOR

def _parse_publish(frame: bytes) -> tuple[str, dict]:
    """Split an MQTT 5 QoS 0 PUBLISH frame into topic and JSON payload."""
    pos = 1
    while frame[pos] & 0x80:
        pos += 1
    pos += 1
    topic_len = int.from_bytes(frame[pos:pos + 2], "big")
    topic = frame[pos + 2:pos + 2 + topic_len].decode()
    body = frame[pos + 2 + topic_len + 1:]  # skip the empty properties byte
    return topic, json.loads(body)



def test_thing_status_maps_freo_s_states() -> None:
    module = _coordinator_module()
    merge = module.merge_thing_status
    base = {"free": True, "in_station": False, "pause": False, "recall": False}

    docked = merge(base, {"robot_status": {"status": 6, "robot_in_station": True,
                                           "fault": 0, "battery_percentage": 94}})
    assert docked["in_station"] is True
    assert docked["battery_percentage"] == 94
    assert docked["fault"] is False

    cleaning = merge(base, {"robot_status": {"status": 4, "robot_in_station": False,
                                             "fault": 0}})
    assert cleaning["free"] is False and cleaning["in_station"] is False
    assert cleaning["pause"] is False and cleaning["recall"] is False

    paused = merge(base, {"robot_status": {"status": 3, "fault": 0}})
    assert paused["pause"] is True

    returning = merge(base, {"robot_status": {"status": 5, "fault": 0}})
    assert returning["recall"] is True

    error = merge(base, {"robot_status": {"status": 7, "fault": 24}})
    assert error["fault"] is True and error["fault_code"] == 24


def test_thing_clean_values_feed_task_sensors() -> None:
    module = _coordinator_module()
    merged = module.merge_thing_status(
        {"extend_data": {"clean": {"cleaning_time": 0}}},
        {"clean": {"cleaning_time": 3, "cleaning_area": 2, "cleaning_progress": 1}},
    )
    assert merged["extend_data"]["clean"] == {
        "cleaning_time": 3,
        "cleaning_area": 2,
        "cleaning_progress": 1,
    }


def test_empty_thing_data_keeps_cloud_status() -> None:
    module = _coordinator_module()
    base = {"in_station": True, "battery_percentage": 50}
    assert module.merge_thing_status(base, {}) == base


def test_thing_request_payload_matches_official_app() -> None:
    """The JSON frame must carry method/actionIdentifier/module/input."""
    mqtt = sys.modules["narwal_cloud.mqtt"]
    sent: list[bytes] = []

    class Writer:
        def write(self, data: bytes) -> None:
            sent.append(data)

        async def drain(self) -> None:
            return None

        def close(self) -> None:
            return None

    replies: list[bytes] = []

    def packet(ptype: int, body: bytes) -> bytes:
        return bytes([ptype << 4]) + mqtt._varint(len(body)) + body

    class Reader:
        def __init__(self) -> None:
            self.buf = b""

        async def readexactly(self, n: int) -> bytes:
            while len(self.buf) < n:
                if replies:
                    self.buf += replies.pop(0)
                else:
                    await asyncio.sleep(0.01)
                    if len(sent) >= 3 and not replies:
                        _topic, payload = _parse_publish(sent[2])
                        reply_topic = (
                            "/P/D/thing/action/request/reply"
                        ).encode()
                        reply = json.dumps(
                            {"code": 0, "method": "invoke",
                             "messageId": payload["messageId"]}
                        ).encode()
                        replies.append(
                            packet(3, len(reply_topic).to_bytes(2, "big")
                                   + reply_topic + b"\x00" + reply)
                        )
            out, self.buf = self.buf[:n], self.buf[n:]
            return out

    replies.extend([packet(2, b"\x00\x00\x00"), packet(9, b"\x00\x01\x00\x00")])

    async def fake_open_connection(*_args, **_kwargs):
        return Reader(), Writer()

    async def run() -> None:
        original = mqtt.asyncio.open_connection
        mqtt.asyncio.open_connection = fake_open_connection
        try:
            result = await mqtt.async_thing_request(
                "mqtts://broker.example:8883", "token", "uuid", "P", "D",
                [("thing/action/request", "thing/action/request/reply",
                  {"method": "invoke", "actionIdentifier": "pause_sweeping",
                   "module": "clean", "input": {}})],
                timeout=2,
            )
        finally:
            mqtt.asyncio.open_connection = original
        assert len(result) == 1
        topic, payload = _parse_publish(sent[2])
        assert topic == "/P/D/thing/action/request"
        assert payload["actionIdentifier"] == "pause_sweeping"
        assert payload["module"] == "clean"
        assert payload["method"] == "invoke"
        assert payload["messageId"]

    asyncio.run(run())


if __name__ == "__main__":
    test_thing_status_maps_freo_s_states()
    test_thing_clean_values_feed_task_sensors()
    test_empty_thing_data_keeps_cloud_status()
    test_thing_request_payload_matches_official_app()
    print("thing model tests passed")
