from __future__ import annotations

import datetime as dt
import zoneinfo
from datetime import datetime, timedelta
from enum import Enum
from typing import Annotated, List, Optional, Tuple, Union

from pydantic import BaseModel, Field
from typing_extensions import Annotated

TIMEZONE_UTC = zoneinfo.ZoneInfo("UTC")


class FilterMatchMode(str, Enum):
    """
    Enumeration for different matching modes used by filters.
    """

    IN = "in"
    EQUALS = "equals"
    CONTAINS = "contains"
    DATE_BEFORE = "dateBefore"
    DATE_AFTER = "dateAfter"
    GREATER_THAN = "greaterThan"
    DATE_IS = "dateIs"
    LESS_THAN = "lessThan"
    BETWEEN = "between"

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            value = value.lower()
            for member in cls:
                if member.value.lower() == value:
                    return member
        return None


class FilterField(BaseModel):
    value: Optional[str] = Field(
        None,
        description="Value used for filtering.",
        examples=["example_value"],
    )
    match_mode: FilterMatchMode = Field(
        ...,
        description="Matching mode to apply for the filter.",
        examples=[FilterMatchMode.EQUALS.value],
    )


class FilterBoolField(BaseModel):
    value: bool = Field(
        False,
        description="Boolean value used for filtering.",
        examples=[True, False],
    )
    match_mode: FilterMatchMode = Field(
        ...,
        description="Matching mode for the boolean filter.",
        examples=[FilterMatchMode.EQUALS.value],
    )


class FilterFieldStringArray(BaseModel):
    value: Optional[List[str]] = Field(
        None,
        description="Array of strings to filter by.",
        examples=[["video", "image"]],
    )
    match_mode: FilterMatchMode = Field(
        ...,
        description="Matching mode to apply on the string array filter.",
        examples=[FilterMatchMode.IN.value],
    )


class FilterFieldDatetime(BaseModel):
    operator: Optional[str] = Field(
        None,
        description="Operator determining the type of datetime filter (e.g. dateBefore, dateAfter).",
        examples=["dateBefore"],
    )
    constraints: List[FilterField] = Field(
        ...,
        description="A list of constraints for the datetime filter.",
    )
    value: Optional[str] = Field(
        None,
        description="A datetime string used for filtering.",
        examples=["2025-01-01T00:00:00.000+0000"],
    )

    def date_range(self) -> Tuple[Optional[datetime], Optional[datetime]]:
        date_format = "%Y-%m-%dT%H:%M:%S.%f%z"
        if self.operator in [
            FilterMatchMode.DATE_IS.value,
            FilterMatchMode.DATE_AFTER.value,
            FilterMatchMode.DATE_BEFORE.value,
        ]:
            if self.constraints and self.constraints[0].value:
                val = self.constraints[0].value
                date_value = dt.datetime.strptime(val, date_format)
                date_value = date_value.astimezone(TIMEZONE_UTC)
                date_value = date_value.replace(tzinfo=None)
                if self.operator == FilterMatchMode.DATE_IS:
                    return (
                        date_value,
                        date_value + timedelta(days=1) if date_value else None,
                    )
                elif self.operator == FilterMatchMode.DATE_AFTER:
                    return (date_value, None)
                elif self.operator == FilterMatchMode.DATE_BEFORE:
                    return (None, date_value)
        else:
            start_date, end_date = None, None
            for constraint in self.constraints:
                if (
                    constraint.match_mode == FilterMatchMode.DATE_AFTER
                    and constraint.value
                ):
                    date_value = dt.datetime.strptime(constraint.value, date_format)
                    date_value = date_value.astimezone(TIMEZONE_UTC)
                    start_date = date_value.replace(tzinfo=None)
                elif (
                    constraint.match_mode == FilterMatchMode.DATE_BEFORE
                    and constraint.value
                ):
                    date_value = dt.datetime.strptime(constraint.value, date_format)
                    date_value = date_value.astimezone(TIMEZONE_UTC)
                    end_date = date_value.replace(tzinfo=None)
            if start_date or end_date:
                return (start_date, end_date)
        return (None, None)


class SortDirection(str, Enum):
    """
    Enumeration for sort directions.
    """

    asc = "asc"
    desc = "desc"


class SearchModel(BaseModel):
    value: Optional[str] = Field(
        ...,
        description="Global search string to match against file attributes.",
        examples=["myfile"],
    )
    field: Annotated[
        str,
        Field(
            ...,
            description="The file attribute to search in (e.g. name, type).",
            examples=["name"],
        ),
    ] = "name"


class OrderingModel(BaseModel):
    field: Annotated[
        Optional[str],
        Field(
            ...,
            description="File attribute to sort by.",
            examples=["modified"],
        ),
    ] = "modified"
    direction: Annotated[
        Optional[SortDirection],
        Field(
            ...,
            description="Sort direction, either ascending or descending.",
            examples=[SortDirection.asc.value],
        ),
    ] = None


class FileFilterModel(BaseModel):
    """
    Model representing criteria for filtering files.
    """

    modified: Annotated[
        Optional[FilterFieldDatetime],
        Field(
            ...,
            description="Filter for file modification dates.",
        ),
    ] = None
    type: Annotated[
        Optional[FilterFieldStringArray],
        Field(
            ...,
            description="Filter by general data category (e.g. text, image, audio, video).",
            examples=[
                {
                    "value": ["video", "image"],
                    "match_mode": FilterMatchMode.IN.value,
                }
            ],
        ),
    ] = None
    content_type: Annotated[
        Optional[FilterFieldStringArray],
        Field(
            ...,
            description="Filter by MIME types of the files.",
            examples=[
                {
                    "value": ["video/mp4", "video/x-msvideo"],
                    "match_mode": FilterMatchMode.IN.value,
                }
            ],
        ),
    ] = None
    file_suffixes: Annotated[
        Optional[FilterFieldStringArray],
        Field(
            ...,
            description="Filter by file suffixes.",
            examples=[
                {
                    "value": [".jpg", ".png"],
                    "match_mode": FilterMatchMode.IN.value,
                }
            ],
        ),
    ] = None


class FileDetail(BaseModel):
    """
    Model providing details of a file.
    """

    name: Annotated[
        str,
        Field(
            ...,
            description="File name relative to its media type directory (without any directory path).",
            examples=["recording_2024-10-04-13-22-54.avi"],
        ),
    ]
    path: Annotated[
        str,
        Field(
            ...,
            description="File path (relative to its media type directory), including any nested directory structure.",
            examples=["nested_videos/recording_2025-01-16-19-12-25.avi"],
        ),
    ]
    size: Annotated[
        Optional[int],
        Field(
            ...,
            description="Size of the file in bytes.",
            examples=[1575142],
        ),
    ]
    is_dir: Annotated[
        bool,
        Field(
            ...,
            description="Flag indicating whether the file is a directory.",
            examples=[False, True],
        ),
    ]
    modified: Annotated[
        Optional[float],
        Field(
            ...,
            description="Timestamp of the most recent modification (in epoch seconds).",
            examples=[1737047576.6511562],
        ),
    ]
    type: Annotated[
        Optional[str],
        Field(
            ...,
            description="General data category (e.g. text, image, audio, video).",
            examples=["video", "image", "audio"],
        ),
    ] = None
    content_type: Annotated[
        Optional[str],
        Field(
            ...,
            description="The MIME type of the file.",
            examples=[
                "video/x-msvideo",
                "video/mp4",
                "application/zip",
                "audio/x-wav",
                "image/jpeg",
                "image/jpg",
            ],
        ),
    ] = None
    duration: Annotated[
        Optional[float],
        Field(
            ...,
            description="Duration (in seconds) for audio or video files.",
            examples=[25.7, 2.733333],
        ),
    ] = None


class GroupedFile(FileDetail):
    children: Annotated[
        Optional[List[GroupedFile]],
        Field(
            ...,
            description="Nested files or directories contained within a directory.",
            examples=[
                [
                    {
                        "name": "nested_videos",
                        "path": "nested_videos",
                        "size": 0,
                        "is_dir": True,
                        "modified": 0,
                        "type": "directory",
                        "content_type": "directory",
                        "duration": None,
                        "children": [
                            {
                                "name": "recording_2025-01-16-19-12-25.avi",
                                "path": "nested_videos/recording_2025-01-16-19-12-25.avi",
                                "size": 395470,
                                "is_dir": False,
                                "modified": 1737047576.6511562,
                                "type": "video",
                                "content_type": "video/x-msvideo",
                                "duration": None,
                            }
                        ],
                    }
                ]
            ],
        ),
    ] = None


class ValueLabelOption(BaseModel):
    value: Annotated[
        str,
        Field(
            ...,
            description="Underlying value of the option.",
            examples=["video"],
        ),
    ]
    label: Annotated[
        str,
        Field(
            ...,
            description="Human-readable label for the option.",
            examples=["Video"],
        ),
    ]


class FilterInfo(BaseModel):
    """
    Model offering available filtering options.
    """

    type: Annotated[
        Optional[Union[List[ValueLabelOption], List[str]]],
        Field(
            ...,
            description="Available categories of data.",
            examples=[["video", "audio"]],
        ),
    ] = None
    file_suffixes: Annotated[
        Optional[Union[List[ValueLabelOption], List[str]]],
        Field(
            ...,
            description="Available file suffix options.",
            examples=[[".hef", ".pt"]],
        ),
    ] = None

    class Config:
        extra = "allow"


class FileResponseModel(BaseModel):
    data: List[GroupedFile] = Field(
        ...,
        description="A list of grouped files and directories.",
    )
    filter_info: FilterInfo = Field(
        ...,
        description="Information about available filters.",
    )
    dir: Optional[str] = Field(
        None,
        description="The subdirectory (relative to its media type directory) that was queried.",
    )
    root_dir: str = Field(
        ...,
        description="The root directory (typically the media type base) for the returned files.",
    )


class FileFilterRequest(BaseModel):
    """
    Model representing compounded filter, search, and ordering criteria for files.
    """

    filters: Annotated[
        Optional[FileFilterModel],
        Field(
            ...,
            description="Filter criteria for files.",
        ),
    ] = None
    search: Optional[SearchModel] = Field(
        None,
        description="Search criteria for files.",
    )
    ordering: Annotated[
        Optional[OrderingModel],
        Field(
            ...,
            description="Ordering criteria for the file list.",
        ),
    ] = None
    dir: Annotated[
        Optional[str],
        Field(
            ...,
            description="The subdirectory within the media type directory to filter files from.",
        ),
    ] = None
