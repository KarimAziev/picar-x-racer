from pydantic import BaseModel, Field


class Message(BaseModel):
    """
    A message response.
    """

    message: str = Field(
        ...,
        description="A message indicating the status or result of an operation.",
        examples=["Saved successfully"],
    )
