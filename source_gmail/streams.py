#
# Copyright (c) 2025 Airbyte, Inc., all rights reserved.
#

import base64
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional

from airbyte_cdk.models import SyncMode
from airbyte_cdk.sources.streams import Stream
from source_gmail.client import GmailClient
from source_gmail.utils import parse_message_headers, parse_message_parts, sanitize_text


class GmailMessagesStream(Stream):
    """
    Stream for reading Gmail messages.
    """
    
    primary_key = "id"
    cursor_field = "internal_date"

    def __init__(self, client: GmailClient, config: Dict[str, Any], **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.config = config

    @property
    def name(self) -> str:
        return "messages"

    def get_json_schema(self) -> Mapping[str, Any]:
        """
        Get the JSON schema for Gmail messages.
        """
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "thread_id": {"type": "string"},
                "label_ids": {
                    "type": ["null", "array"],
                    "items": {"type": "string"}
                },
                "from": {"type": ["null", "string"]},
                "to": {"type": ["null", "string"]},
                "cc": {"type": ["null", "string"]},
                "bcc": {"type": ["null", "string"]},
                "subject": {"type": ["null", "string"]},
                "date": {"type": ["null", "string"]},
                "internal_date": {"type": ["null", "string"], "format": "date-time"},
                "snippet": {"type": ["null", "string"]},
                "body_plain": {"type": ["null", "string"]},
                # "body_html": {"type": ["null", "string"]},
                "attachments": {
                    "type": ["null", "array"],
                    "items": {
                        "type": "object",
                        "properties": {
                            "filename": {"type": ["null", "string"]},
                            "mime_type": {"type": ["null", "string"]},
                            "size": {"type": ["null", "integer"]},
                            "attachment_id": {"type": ["null", "string"]}
                        }
                    }
                },
                "size_estimate": {"type": ["null", "integer"]},
                "history_id": {"type": ["null", "string"]},
                "raw": {"type": ["null", "string"]}
            },
            "additionalProperties": True
        }

    def read_records(
        self,
        sync_mode: SyncMode,
        cursor_field: Optional[List[str]] = None,
        stream_slice: Optional[Mapping[str, Any]] = None,
        stream_state: Optional[Mapping[str, Any]] = None,
    ) -> Iterable[Mapping[str, Any]]:
        """
        Read Gmail messages.
        """
        page_token = None
        
        # For incremental sync, check if we have a state
        if sync_mode == SyncMode.incremental and stream_state and self.cursor_field in stream_state:
            # Get the last sync timestamp
            last_sync_ms = stream_state[self.cursor_field]
            # Convert to seconds and create a date filter
            last_sync_date = datetime.fromtimestamp(int(last_sync_ms) / 1000, tz=timezone.utc)
            # Format date for Gmail query (YYYY/MM/DD)
            date_filter = f"after:{last_sync_date.year}/{last_sync_date.month}/{last_sync_date.day}"
            
            # Add to existing query
            existing_query = self.config.get("query", "")
            if existing_query:
                query = f"{existing_query} {date_filter}"
            else:
                query = date_filter
            
        else:
            query = self.config.get("query", "")
        
        while True:
            # List messages
            response = self.client.list_messages(
                query=query,
                label_ids=self.config.get("labels"),
                page_token=page_token
            )
            
            messages = response.get("messages", [])
            
            # Fetch full message details for each message
            for msg_ref in messages:
                try:
                    # Get full message
                    message = self.client.get_message(msg_ref["id"])
                    
                    # Parse message data
                    headers = parse_message_headers(message.get("payload", {}).get("headers", []))
                    body_plain, body_html, attachments = parse_message_parts(message.get("payload", {}))
                    
                    # Convert internal date to datetime with RFC 3339 format
                    internal_date_ms = int(message.get("internalDate", 0))
                    internal_date = datetime.fromtimestamp(internal_date_ms / 1000, tz=timezone.utc).isoformat()
                    
                    record = {
                        "id": message["id"],
                        "thread_id": message.get("threadId"),
                        "label_ids": message.get("labelIds", []),
                        "from": headers.get("from"),
                        "to": headers.get("to"),
                        "cc": headers.get("cc"),
                        "bcc": headers.get("bcc"),
                        "subject": headers.get("subject"),
                        "date": headers.get("date"),
                        "internal_date": internal_date,
                        "snippet": message.get("snippet"),
                        "body_plain": sanitize_text(body_plain),
                        # "body_html": body_html,
                        "attachments": attachments,
                        "size_estimate": message.get("sizeEstimate"),
                        "history_id": message.get("historyId"),
                    }
                    
                    # Optionally include raw message
                    if self.config.get("include_raw", False):
                        record["raw"] = message.get("raw")
                    
                    yield record
                    
                except Exception as e:
                    self.logger.error(f"Error processing message {msg_ref['id']}: {str(e)}")
                    continue
            
            # Check for next page
            page_token = response.get("nextPageToken")
            if not page_token:
                break
    
    def get_updated_state(self, current_stream_state: Mapping[str, Any], latest_record: Mapping[str, Any]) -> Mapping[str, Any]:
        """
        Update the state with the latest record's cursor field value.
        """
        if not latest_record:
            return current_stream_state
        
        # Get the cursor value from the latest record
        latest_cursor_value = latest_record.get(self.cursor_field)
        if not latest_cursor_value:
            return current_stream_state
        
        # Convert ISO datetime to milliseconds timestamp
        if isinstance(latest_cursor_value, str):
            dt = datetime.fromisoformat(latest_cursor_value.replace('Z', '+00:00'))
            latest_cursor_value = int(dt.timestamp() * 1000)
        
        # Update state if this record is newer
        current_cursor_value = current_stream_state.get(self.cursor_field, 0)
        if latest_cursor_value > current_cursor_value:
            return {self.cursor_field: latest_cursor_value}
        
        return current_stream_state


class GmailLabelsStream(Stream):
    """
    Stream for reading Gmail labels.
    """
    
    primary_key = "id"

    def __init__(self, client: GmailClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client

    @property
    def name(self) -> str:
        return "labels"

    def get_json_schema(self) -> Mapping[str, Any]:
        """
        Get the JSON schema for Gmail labels.
        """
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "type": {"type": ["null", "string"]},
                "messages_total": {"type": ["null", "integer"]},
                "messages_unread": {"type": ["null", "integer"]},
                "threads_total": {"type": ["null", "integer"]},
                "threads_unread": {"type": ["null", "integer"]},
                "color": {
                    "type": ["null", "object"],
                    "properties": {
                        "text_color": {"type": ["null", "string"]},
                        "background_color": {"type": ["null", "string"]}
                    }
                }
            },
            "additionalProperties": True
        }

    def read_records(
        self,
        sync_mode: SyncMode,
        cursor_field: Optional[List[str]] = None,
        stream_slice: Optional[Mapping[str, Any]] = None,
        stream_state: Optional[Mapping[str, Any]] = None,
    ) -> Iterable[Mapping[str, Any]]:
        """
        Read Gmail labels.
        """
        labels = self.client.get_labels()
        
        for label in labels:
            record = {
                "id": label["id"],
                "name": label["name"],
                "type": label.get("type"),
                "messages_total": label.get("messagesTotal"),
                "messages_unread": label.get("messagesUnread"),
                "threads_total": label.get("threadsTotal"),
                "threads_unread": label.get("threadsUnread"),
            }
            
            # Add color info if available
            if "color" in label:
                record["color"] = {
                    "text_color": label["color"].get("textColor"),
                    "background_color": label["color"].get("backgroundColor")
                }
            
            yield record