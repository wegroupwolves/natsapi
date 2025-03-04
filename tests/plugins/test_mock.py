import asyncio

import pytest

from natsapi.plugin import NatsapiMock

pytestmark = pytest.mark.asyncio
ch = "service"


async def test_nats_mock_wrong_host_should_raise_error():
    with pytest.raises(Exception):
        mock = NatsapiMock(host="foobar", channel="foobar")
        await mock.wait_startup()


async def test_nats_mock_should_respond_with_mocked_response(app, natsapi_mock):
    # given:
    await natsapi_mock.request(f"{ch}.items.retrieve", response={"items": [{"id": 1}]})

    # when:
    reply = await app.nc.request(f"{ch}.items.retrieve", timeout=1)

    # then:
    assert not reply.error
    assert reply.result == {"items": [{"id": 1}]}, reply.result


async def test_nats_mock_should_respond_with_mocked_response_given_a_model(app, natsapi_mock):
    from pydantic import BaseModel

    class Foo(BaseModel):
        items: list[str]

    # given:
    await natsapi_mock.request(f"{ch}.items.retrieve", response=Foo(items=["a", "b"]))

    # when:
    reply = await app.nc.request(f"{ch}.items.retrieve", timeout=1)

    # then:
    assert not reply.error
    assert reply.result == {"items": ["a", "b"]}, reply.result


async def test_be_able_to_intercept_nats_request_payload(app, natsapi_mock):
    # given:
    await natsapi_mock.request(f"{ch}.items.id.retrieve", response={"id": 1})

    # when:
    payload = {"id": 1}
    await app.nc.request(f"{ch}.items.id.retrieve", payload, timeout=1)

    # then:
    assert len(natsapi_mock.payloads[f"{ch}.items.id.retrieve"]) == 1, natsapi_mock.payloads
    payload = natsapi_mock.payloads[f"{ch}.items.id.retrieve"][0]
    assert payload["params"]["id"] == 1


async def test_nats_mock_should_respond_with_mocked_error_when_error(app, natsapi_mock):
    # given:
    await natsapi_mock.request(f"{ch}.items.retrieve", error={"code": -1, "message": "FOOBAR"})

    # when:
    reply = await app.nc.request(f"{ch}.items.retrieve", timeout=1)

    # then:
    assert reply.error.message == "FOOBAR"


async def test_nats_mock_should_raise_error_when_invalid_error_response(app, natsapi_mock):
    # given: an invalid JsonRPCError response that is not a dict
    await natsapi_mock.request(f"{ch}.items.retrieve", error="ERROR")

    # when:
    reply = await app.nc.request(f"{ch}.items.retrieve", timeout=1)

    # then:
    assert "valid dict" in reply.error.message


async def test_be_able_to_intercept_nats_publish_event_payload(app, natsapi_mock):
    # given:
    subject = "a.publish.event"
    await natsapi_mock.publish(subject)

    # when:
    payload = {"id": 1}
    await app.nc.publish(subject, payload)

    # wait 1 second to be sure publish event is picked up
    await asyncio.sleep(1)

    # then:
    assert len(natsapi_mock.payloads) == 1
    assert natsapi_mock.payloads[subject][0]["params"] == payload
