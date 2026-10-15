from typing import Literal

from pydantic import BaseModel, Field


class Connexion(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class Jeton(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Literal["exploitant", "direction"]
