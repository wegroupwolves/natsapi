#! /usr/bin/python

import json

import httpx
import nats
from fastapi import FastAPI, Request
from pydantic import BaseModel

app = FastAPI()


@app.on_event("startup")
async def setup() -> None:
    try:
        app.nc = await nats.connect("nats://localhost:4222")
    except Exception as e:
        print(e)


@app.get("/nats/index")
async def nats_index(request: Request):
    response = await request.app.nc.request("index", b"", timeout=60)
    return json.loads(response.data.decode())


@app.get("/rest/index")
async def rest_index():
    async with httpx.AsyncClient() as client:
        r = await client.get("http://localhost:5001/index")
    return r.json()


class Numbers(BaseModel):
    number_1: int
    number_2: int


@app.post("/nats/sum")
async def nats_sum(request: Request, numbers: Numbers):
    response = await request.app.nc.request("sum", numbers.json().encode(), timeout=60)
    return json.loads(response.data.decode())


@app.post("/rest/sum")
async def rest_sum(numbers: Numbers):
    async with httpx.AsyncClient() as client:
        r = await client.post("http://localhost:5001/sum", json=numbers.dict())
    return r.text
