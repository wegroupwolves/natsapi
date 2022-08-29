import logging

from natsapi import NatsAPI

logging.basicConfig(level=logging.INFO)

app = NatsAPI("natsapi.dev")


@app.on_startup
async def setup():
    logging.info("Connect to db")


@app.on_shutdown
async def teardown():
    logging.info("Disconnect from db")


if __name__ == "__main__":
    app.run()
