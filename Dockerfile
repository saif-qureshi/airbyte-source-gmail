FROM airbyte/python-connector-base:4.0.2

WORKDIR /airbyte/integration_code

# Copy and install dependencies
COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-interaction --no-ansi

# Copy the source code
COPY . .

# Install the connector package itself
RUN poetry install --only-root --no-interaction --no-ansi

# Set the entrypoint (make sure main.py exists)
ENV AIRBYTE_ENTRYPOINT="python /airbyte/integration_code/main.py"

# Add these labels
LABEL io.airbyte.version=0.1.3
LABEL io.airbyte.name=airbyte/source-gmail