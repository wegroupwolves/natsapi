from natsapi import NatsAPI


async def test_send_publish_should_be_called(client_config, event_loop):
    app = NatsAPI("natsapi.development", client_config=client_config)
    app.count = 0

    @app.publish(subject="foo")
    async def _(app):
        app.count += 1

    await app.startup(loop=event_loop)
    await app.nc.publish("natsapi.development.foo", {})
    await app.shutdown(app)
    assert app.count == 1
