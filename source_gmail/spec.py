#
# Copyright (c) 2025 Airbyte, Inc., all rights reserved.
#

from typing import Any, Dict, List, Literal, Mapping, Optional

from pydantic.v1 import BaseModel, Field


class SourceGmailSpec(BaseModel):
    """
    Spec for source-gmail.
    """
    
    class Config:
        title = "Gmail Source Spec"
        schema_extra = {
            "documentationUrl": "https://docs.airbyte.com/integrations/sources/gmail",
        }

    client_id: str = Field(
        ...,
        title="Client ID",
        description="The Client ID of your Google Cloud application",
        airbyte_secret=True,
        order=0,
    )

    client_secret: str = Field(
        ...,
        title="Client Secret",
        description="The Client Secret of your Google Cloud application",
        airbyte_secret=True,
        order=10,
    )

    refresh_token: str = Field(
        ...,
        title="Refresh Token",
        description="Refresh token obtained from Google OAuth flow",
        airbyte_secret=True,
        order=20,
    )

    include_spam_trash: bool = Field(
        default=False,
        title="Include Spam and Trash",
        description="Include messages from SPAM and TRASH folders",
        order=30,
    )