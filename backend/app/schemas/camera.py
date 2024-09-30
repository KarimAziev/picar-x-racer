from pydantic import BaseModel


class PhotoResponse(BaseModel):
    """
    A response object containing the filename of the captured photo
    """

    file: str


class FrameDimensionsResponse(BaseModel):
    """
    A response object containing the width and height of the current camera frame.
    """

    width: int
    height: int
