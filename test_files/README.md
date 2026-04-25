## Test Inputs

These files simulate clinical prompts uploaded to S3.

They are used to trigger the event-driven pipeline:
S3 → Lambda → FastAPI → LLM → S3

Each file contains a plain-text prompt.
