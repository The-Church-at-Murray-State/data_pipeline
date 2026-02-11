from dataclasses import dataclass
from pydantic import BaseModel

@dataclass(frozen=True)
class Endpoint:
    path: str
    method: str
    request_scheme: type[BaseModel] | None = None
    response_scheme: type[BaseModel] | None = None
    