#! /usr/bin/python

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


@app.get("/index")
async def index():
    return {"Hello": "World"}


class Numbers(BaseModel):
    number_1: int
    number_2: int


@app.post("/sum")
async def sum(numbers: Numbers):
    return numbers.number_1 + numbers.number_2
