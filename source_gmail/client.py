#
# Copyright (c) 2025 Airbyte, Inc., all rights reserved.
#

import base64
from typing import Any, Dict, List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from airbyte_cdk import AirbyteTracedException, FailureType
from source_gmail.spec import SourceGmailSpec


class GmailClient:
    """
    Client to interact with Gmail API.
    """

    def __init__(self, config: SourceGmailSpec):
        self.config = config
        self._service = None
        self._credentials = None

    @property
    def credentials(self):
        """Get OAuth2 credentials."""
        if not self._credentials:
            self._credentials = Credentials(
                token=None,
                refresh_token=self.config.refresh_token,
                client_id=self.config.client_id,
                client_secret=self.config.client_secret,
                token_uri="https://oauth2.googleapis.com/token",
                scopes=["https://www.googleapis.com/auth/gmail.readonly"]
            )
            # Refresh the token
            self._credentials.refresh(Request())
        return self._credentials

    @property
    def service(self):
        """Get Gmail service instance."""
        if not self._service:
            self._service = build('gmail', 'v1', credentials=self.credentials)
        return self._service

    def check_connection(self) -> bool:
        """Check if we can connect to Gmail API."""
        try:
            # Try to get user profile
            self.service.users().getProfile(userId='me').execute()
            return True
        except Exception:
            return False

    def get_user_email(self) -> str:
        """Get the authenticated user's email address."""
        try:
            profile = self.service.users().getProfile(userId='me').execute()
            return profile.get('emailAddress', 'unknown')
        except Exception:
            return 'unknown'

    def get_labels(self) -> List[Dict[str, Any]]:
        """Get all labels from the mailbox."""
        try:
            results = self.service.users().labels().list(userId='me').execute()
            return results.get('labels', [])
        except HttpError as error:
            raise AirbyteTracedException(
                internal_message=f"Failed to get labels: {error}",
                message="Failed to retrieve Gmail labels. Please check your permissions.",
                failure_type=FailureType.config_error,
            )

    def list_messages(self, query: str = "", label_ids: Optional[List[str]] = None, page_token: Optional[str] = None) -> Dict[str, Any]:
        """List messages matching the query."""
        try:
            kwargs = {
                'userId': 'me',
                'maxResults': 100,  # Default batch size
            }
            
            if query:
                kwargs['q'] = query
            
            if label_ids:
                kwargs['labelIds'] = label_ids
            
            if page_token:
                kwargs['pageToken'] = page_token
            
            # Build query with filters
            query_parts = []
            
            if query:
                query_parts.append(query)
            
            # Add spam/trash filter
            if not self.config.include_spam_trash:
                query_parts.append("-in:spam -in:trash")
            
            # Add start date filter if provided
            if self.config.start_date:
                # Convert ISO format to Gmail query format (YYYY/MM/DD)
                # Example: 2024-01-01T00:00:00.000000Z -> after:2024/1/1
                try:
                    date_part = self.config.start_date.split('T')[0]  # Get YYYY-MM-DD part
                    year, month, day = date_part.split('-')
                    gmail_date = f"{year}/{int(month)}/{int(day)}"  # Remove leading zeros
                    query_parts.append(f"after:{gmail_date}")
                except:
                    # If parsing fails, use the date as-is
                    query_parts.append(f"after:{self.config.start_date}")
            
            if query_parts:
                kwargs['q'] = " ".join(query_parts)
            
            return self.service.users().messages().list(**kwargs).execute()
        
        except HttpError as error:
            raise AirbyteTracedException(
                internal_message=f"Failed to list messages: {error}",
                message="Failed to list Gmail messages. Please check your query and permissions.",
                failure_type=FailureType.system_error,
            )

    def get_message(self, message_id: str) -> Dict[str, Any]:
        """Get a single message by ID."""
        try:
            return self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
        except HttpError as error:
            raise AirbyteTracedException(
                internal_message=f"Failed to get message {message_id}: {error}",
                message=f"Failed to retrieve message. It may have been deleted.",
                failure_type=FailureType.system_error,
            )

    def get_attachment(self, message_id: str, attachment_id: str) -> Dict[str, Any]:
        """Get an attachment from a message."""
        try:
            return self.service.users().messages().attachments().get(
                userId='me',
                messageId=message_id,
                id=attachment_id
            ).execute()
        except HttpError as error:
            raise AirbyteTracedException(
                internal_message=f"Failed to get attachment {attachment_id}: {error}",
                message="Failed to retrieve attachment.",
                failure_type=FailureType.system_error,
            )