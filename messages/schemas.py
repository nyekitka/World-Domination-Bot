from pydantic import BaseModel


class Message(BaseModel):
    template: str
    markdown: bool = False
