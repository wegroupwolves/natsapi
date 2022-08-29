from natsapi import NatsAPI
from natsapi.client import Config, SubscribeConfig


def test_customize_config_should_use_customized_config():
    subscribe = SubscribeConfig(queue="smt")
    client_config = Config(subscribe=subscribe)

    app = NatsAPI("natsapi.development", client_config=client_config)

    assert app.client_config.subscribe.queue == client_config.subscribe.queue
