import json
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()


@logger.inject_lambda_context
def handler(event: dict, context: LambdaContext) -> dict:
    """
    Handler for WebSocket API connect requests
    """
    connection_id = event["requestContext"]["connectionId"]
    logger.info(
        "Client connected",
        extra={
            "connection_id": connection_id,
            "event_type": "CONNECT",
            "request_context": event["requestContext"],
        },
    )

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Connected successfully"}),
    }
