import json
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()


@logger.inject_lambda_context
def handler(event: dict, context: LambdaContext) -> dict:
    """
    Handler for WebSocket API default route (receiving messages)
    """
    connection_id = event["requestContext"]["connectionId"]
    body = event

    logger.info(
        "Message received",
        extra={
            "connection_id": connection_id,
            "event_type": "MESSAGE",
            "request_context": event["requestContext"],
            "event": body,
        },
    )

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Message received successfully"}),
    }
