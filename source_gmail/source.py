#
# Copyright (c) 2025 Airbyte, Inc., all rights reserved.
#

from typing import Any, List, Mapping, Tuple

from airbyte_cdk import AirbyteTracedException, FailureType
from airbyte_cdk.models import ConnectorSpecification, SyncMode
from airbyte_cdk.sources import AbstractSource
from airbyte_cdk.sources.streams import Stream
from source_gmail.client import GmailClient
from source_gmail.spec import SourceGmailSpec
from source_gmail.streams import GmailMessagesStream, GmailLabelsStream


class SourceGmail(AbstractSource):
    def check_connection(self, logger, config: Mapping[str, Any]) -> Tuple[bool, Any]:
        """
        Check connection to Gmail API.
        """
        try:
            spec = SourceGmailSpec(**config)
            client = GmailClient(spec)
            
            # Try to connect and get user profile
            if client.check_connection():
                email = client.get_user_email()
                return True, f"Successfully connected to Gmail account: {email}"
            else:
                return False, "Failed to connect to Gmail API"
            
        except Exception as e:
            return False, f"Failed to connect: {str(e)}"

    def streams(self, config: Mapping[str, Any]) -> List[Stream]:
        """
        Return the list of streams.
        """
        spec = SourceGmailSpec(**config)
        client = GmailClient(spec)
        
        try:
            streams = [
                GmailMessagesStream(client=client, config=config),
                GmailLabelsStream(client=client),
            ]
            
            return streams
            
        except Exception as e:
            raise AirbyteTracedException(
                message=f"Failed to discover streams: {str(e)}",
                internal_message=str(e),
                failure_type=FailureType.config_error,
                exception=e,
            )

    def spec(self, *args, **kwargs) -> ConnectorSpecification:
        """
        Returns the specification for this source.
        """
        return ConnectorSpecification(
            documentationUrl="https://docs.airbyte.com/integrations/sources/gmail",
            connectionSpecification=SourceGmailSpec.schema(),
        )