# Built-in imports
import os

# External imports
from aws_cdk import (
    Stack,
    Duration,
    aws_lambda,
    aws_apigatewayv2 as aws_apigwv2,
    aws_apigatewayv2_integrations as aws_apigwv2_integrations,
    CfnOutput,
)
from constructs import Construct


class BackendStack(Stack):
    """
    Class to create the backend resources, which includes the DynamoDB database,
    Lambda Functions, APIs, Roles and additional resources for the TODO app solution on AWS.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        main_resources_name: str,
        app_config: dict[str],
        **kwargs,
    ) -> None:
        """
        :param scope (Construct): Parent of this stack, usually an 'App' or a 'Stage', but could be any construct.
        :param construct_id (str): The construct ID of this stack (same as aws-cdk Stack 'construct_id').
        :param main_resources_name (str): The main unique identified of this stack.
        :param app_config (dict[str]): Dictionary with relevant configuration values for the stack.
        """
        super().__init__(scope, construct_id, **kwargs)

        # Input parameters
        self.construct_id = construct_id
        self.main_resources_name = main_resources_name
        self.app_config = app_config
        self.deployment_environment = self.app_config["deployment_environment"]

        # Main methods for the deployment
        self.create_lambda_layers()
        self.create_lambda_functions()
        self.create_websocket_api()

        # Create CloudFormation outputs
        self.generate_cloudformation_outputs()

    def create_lambda_layers(self) -> None:
        """
        Create the Lambda layers that are necessary for the additional runtime
        dependencies of the Lambda Functions.
        """

        # Layer for "LambdaPowerTools" (for logging, traces, observability, etc)
        self.lambda_layer_powertools = aws_lambda.LayerVersion.from_layer_version_arn(
            self,
            "Layer-powertools",
            layer_version_arn=f"arn:aws:lambda:{self.region}:017000801446:layer:AWSLambdaPowertoolsPythonV2:71",
        )

    def create_lambda_functions(self) -> None:
        """
        Create the Lambda Functions for the solution.
        """
        # Get relative path for folder that contains Lambda function source
        # ! Note--> we must obtain parent dirs to create path (that"s why there is "os.path.dirname()")
        PATH_TO_LAMBDA_FUNCTION_FOLDER = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "backend",
        )

        # WebSocket Connect Handler
        self.lambda_ws_connect = aws_lambda.Function(
            self,
            "Lambda-ws-connect",
            runtime=aws_lambda.Runtime.PYTHON_3_11,
            function_name=f"{self.main_resources_name}-ws-connect-{self.deployment_environment}",
            handler="api/websocket/connect.handler",
            code=aws_lambda.Code.from_asset(PATH_TO_LAMBDA_FUNCTION_FOLDER),
            timeout=Duration.seconds(20),
            memory_size=512,
            environment={
                "ENVIRONMENT": self.app_config["deployment_environment"],
                "LOG_LEVEL": self.app_config["log_level"],
            },
            layers=[
                self.lambda_layer_powertools,
            ],
        )

        # WebSocket Disconnect Handler
        self.lambda_ws_disconnect = aws_lambda.Function(
            self,
            "Lambda-ws-disconnect",
            runtime=aws_lambda.Runtime.PYTHON_3_11,
            function_name=f"{self.main_resources_name}-ws-disconnect-{self.deployment_environment}",
            handler="api/websocket/disconnect.handler",
            code=aws_lambda.Code.from_asset(PATH_TO_LAMBDA_FUNCTION_FOLDER),
            timeout=Duration.seconds(20),
            memory_size=512,
            environment={
                "ENVIRONMENT": self.app_config["deployment_environment"],
                "LOG_LEVEL": self.app_config["log_level"],
            },
            layers=[
                self.lambda_layer_powertools,
            ],
        )

        # WebSocket Default Handler
        self.lambda_ws_default = aws_lambda.Function(
            self,
            "Lambda-ws-default",
            runtime=aws_lambda.Runtime.PYTHON_3_11,
            function_name=f"{self.main_resources_name}-ws-default-{self.deployment_environment}",
            handler="api/websocket/default.handler",
            code=aws_lambda.Code.from_asset(PATH_TO_LAMBDA_FUNCTION_FOLDER),
            timeout=Duration.seconds(20),
            memory_size=512,
            environment={
                "ENVIRONMENT": self.app_config["deployment_environment"],
                "LOG_LEVEL": self.app_config["log_level"],
            },
            layers=[
                self.lambda_layer_powertools,
            ],
        )

    def create_websocket_api(self):
        """
        Method to create and configure the WebSocket API Gateway
        """
        # Create the WebSocket API
        self.websocket_api = aws_apigwv2.WebSocketApi(
            self,
            "WebSocketAPI",
            api_name=f"{self.app_config['api_gw_name']}-ws",
            description=f"WebSocket API for {self.main_resources_name}",
        )

        # Create connect integration
        connect_integration = aws_apigwv2_integrations.WebSocketLambdaIntegration(
            "ConnectIntegration", handler=self.lambda_ws_connect
        )

        # Create default integration
        default_integration = aws_apigwv2_integrations.WebSocketLambdaIntegration(
            "DefaultIntegration", handler=self.lambda_ws_default
        )

        # Create disconnect integration
        disconnect_integration = aws_apigwv2_integrations.WebSocketLambdaIntegration(
            "DisconnectIntegration", handler=self.lambda_ws_disconnect
        )

        # Add routes for connect, disconnect and default
        self.websocket_api.add_route("$connect", integration=connect_integration)
        self.websocket_api.add_route("$default", integration=default_integration)
        self.websocket_api.add_route("$disconnect", integration=disconnect_integration)

        # Create the WebSocket Stage
        self.websocket_stage = aws_apigwv2.WebSocketStage(
            self,
            "WebSocketStage",
            web_socket_api=self.websocket_api,
            stage_name=self.deployment_environment,
            auto_deploy=True,
        )

    def generate_cloudformation_outputs(self) -> None:
        """
        Method to add the relevant CloudFormation outputs.
        """

        CfnOutput(
            self,
            "DeploymentEnvironment",
            value=self.app_config["deployment_environment"],
            description="Deployment environment",
        )

        # Add CloudFormation output for WebSocket API URL
        CfnOutput(
            self,
            "WebSocketApiUrl",
            value=self.websocket_stage.url,
            description="WebSocket API URL",
        )
