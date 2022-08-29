from natsapi import NatsAPI
import asyncio


async def main():
    app = await NatsAPI("client").startup()

    params = {"person": {"first_name": "Foo", "last_name": "Bar"}}
    r = await app.nc.request("natsapi.persons.greet", params=params, timeout=5)
    print(r.result)


asyncio.run(main())
