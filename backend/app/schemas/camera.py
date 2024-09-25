from pydantic import BaseModel


class PhotoResponse(BaseModel):
    file: str


class FrameDimensionsResponse(BaseModel):
    width: int
    height: int
