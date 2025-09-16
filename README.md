# Gmail Source

This is the repository for the Gmail source connector, written in Python.
For information about how to use this connector within Airbyte, see [the documentation](https://docs.airbyte.com/integrations/sources/gmail).

## Local development

### Prerequisites

- Python 3.10+
- Poetry
- A Google Cloud project with Gmail API enabled
- OAuth2.0 credentials (client ID, client secret, and refresh token)

### Installing the connector

From this connector directory, run:
```bash
poetry install
```

### Authentication Setup

This connector uses Gmail API and requires OAuth2.0 authentication:

1. Create a Google Cloud project and enable Gmail API
2. Create OAuth2.0 credentials (Web application type)
3. Add authorized redirect URIs for your OAuth flow
4. Complete the OAuth consent flow to obtain a refresh token
5. Required scopes:
   - https://www.googleapis.com/auth/gmail.readonly

### Create configuration

Create a `secrets/config.json` file:
```json
{
  "client_id": "your-client-id",
  "client_secret": "your-client-secret",
  "refresh_token": "your-refresh-token",
  "include_spam_trash": false
}
```

### Testing

```bash
# Test the connection
poetry run python main.py check --config secrets/config.json

# Discover available streams
poetry run python main.py discover --config secrets/config.json

# Read data
poetry run python main.py read --config secrets/config.json --catalog configured_catalog.json
```

### Using the connector

```bash
poetry run source-gmail spec
poetry run source-gmail check --config secrets/config.json
poetry run source-gmail discover --config secrets/config.json
poetry run source-gmail read --config secrets/config.json --catalog configured_catalog.json
```

## Features

- **Two Streams**: 
  - `messages`: Fetches Gmail messages with headers, body (plain/HTML), and attachment metadata
  - `labels`: Fetches Gmail labels with message/thread counts
- OAuth2.0 authentication with refresh token support
- Configurable spam/trash inclusion
- Batch processing for efficient API usage
- Automatic token refresh

## Architecture

This connector is built using the Python CDK with:
- **Python-based streams**: Direct Gmail API integration
- **OAuth Authentication**: Uses Google Auth library for token management
- **Batch Processing**: Efficiently fetches messages in configurable batch sizes
- **Message Parsing**: Extracts plain text, HTML content, and attachment information

## Key Features

1. **Full Message Content**: Retrieves complete message data including headers and body
2. **Attachment Metadata**: Lists attachments without downloading the actual files
3. **Label Statistics**: Provides message and thread counts for each label
4. **Flexible Filtering**: Option to include or exclude spam and trash messages

## Testing with Real Data

1. Set up OAuth2.0 credentials in Google Cloud Console
2. Complete OAuth flow to obtain refresh token
3. Create config file with your credentials
4. Run check command to verify authentication
5. Run discover to see available streams (messages, labels)
6. Run read to sync Gmail data

