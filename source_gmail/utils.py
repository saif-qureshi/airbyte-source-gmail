#
# Copyright (c) 2025 Airbyte, Inc., all rights reserved.
#

import base64
import re
from typing import Any, Dict, List, Optional, Tuple


def parse_message_headers(headers: List[Dict[str, str]]) -> Dict[str, str]:
    """
    Parse message headers into a dictionary.
    """
    header_dict = {}
    for header in headers:
        name = header.get("name", "").lower()
        value = header.get("value", "")
        
        # Store common headers
        if name in ["from", "to", "cc", "bcc", "subject", "date", "message-id", "reply-to"]:
            header_dict[name.replace("-", "_")] = value
    
    return header_dict


def parse_message_parts(payload: Dict[str, Any]) -> Tuple[Optional[str], Optional[str], List[Dict[str, Any]]]:
    """
    Parse message parts to extract plain text, HTML, and attachments.
    Returns: (plain_text, html_text, attachments)
    """
    plain_text = None
    html_text = None
    attachments = []
    
    def process_part(part: Dict[str, Any]):
        nonlocal plain_text, html_text, attachments
        
        mime_type = part.get("mimeType", "")
        body = part.get("body", {})
        
        # Check if it's an attachment
        if part.get("filename"):
            attachment = {
                "filename": part["filename"],
                "mime_type": mime_type,
                "size": body.get("size", 0),
                "attachment_id": body.get("attachmentId")
            }
            attachments.append(attachment)
        
        # Process text content
        elif mime_type == "text/plain" and plain_text is None:
            data = body.get("data", "")
            if data:
                plain_text = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
        
        elif mime_type == "text/html" and html_text is None:
            data = body.get("data", "")
            if data:
                html_text = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
        
        # Process multipart
        if "parts" in part:
            for subpart in part["parts"]:
                process_part(subpart)
    
    # Start processing from the root payload
    if "parts" in payload:
        for part in payload["parts"]:
            process_part(part)
    else:
        # Single part message
        process_part(payload)
    
    return plain_text, html_text, attachments


def convert_to_rfc3339(timestamp_ms: int) -> str:
    """
    Convert millisecond timestamp to RFC3339 format.
    """
    from datetime import datetime
    dt = datetime.fromtimestamp(timestamp_ms / 1000)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def sanitize_text(text: Optional[str]) -> Optional[str]:
    """
    Sanitize plain text content by removing excessive whitespace and cleaning up formatting.
    """
    if not text:
        return text
    
    # Remove carriage returns
    text = text.replace('\r', '')
    
    # Remove tabs and replace with single space
    text = text.replace('\t', ' ')
    
    # Remove zero-width spaces and other invisible characters
    text = re.sub(r'[\u200b\u200c\u200d\ufeff\u00ad]', '', text)
    
    # Remove excessive spaces (more than 2 consecutive)
    text = re.sub(r' {2,}', ' ', text)
    
    # Split into lines and process each
    lines = text.split('\n')
    
    # Remove leading/trailing whitespace from each line and filter empty lines
    processed_lines = []
    for line in lines:
        line = line.strip()
        if line:  # Only keep non-empty lines
            processed_lines.append(line)
    
    # Join lines back together
    text = '\n'.join(processed_lines)
    
    # Add paragraph breaks where there are multiple consecutive line breaks
    text = re.sub(r'\n{2,}', '\n\n', text)
    
    # Clean up URLs - remove tracking parameters and clean up formatting
    # This regex finds URLs and removes common tracking parameters
    text = re.sub(r'\?utm_[^)\s]*', '', text)
    text = re.sub(r'&utm_[^)\s]*', '', text)
    
    # Remove parentheses around URLs if they're standalone
    text = re.sub(r'\(\s*(https?://[^\s)]+)\s*\)', r' \1', text)
    
    # Final cleanup - remove any remaining multiple spaces
    text = re.sub(r' +', ' ', text)
    
    # Remove empty lines at the beginning and end
    text = text.strip()
    
    return text