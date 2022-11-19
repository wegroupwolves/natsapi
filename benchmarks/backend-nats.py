import asyncio
import json

from nats.aio.client import Client as NATS

nc = NATS()


async def handle_index(msg):
    data = {"hello": "world"}
    await nc.publish(msg.reply, json.dumps(data).encode())


async def handle_sum(msg):
    data = json.loads(msg.data.decode())
    response = str(data["number_1"] + data["number_2"])
    await nc.publish(msg.reply, response.encode())


async def main():
    await nc.connect("nats://127.0.0.1:4222")
    await nc.subscribe("index", "", handle_index)
    await nc.subscribe("sum", "", handle_sum)
    print("Listening for requests")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
        loop.run_forever()
        loop.close()
    except Exception as e:
        print(e)
