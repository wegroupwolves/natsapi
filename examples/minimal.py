from pydantic import BaseModel

from natsapi import NatsAPI, SubjectRouter


class Message(BaseModel):
    message: str


class Person(BaseModel):
    first_name: str
    last_name: str


app = NatsAPI("natsapi")
router = SubjectRouter()


@router.request("persons.greet", result=Message)
async def greet_person(app: NatsAPI, person: Person):
    return {"message": f"Greetings {person.first_name} {person.last_name}!"}


app.include_router(router)

if __name__ == "__main__":
    app.run()
