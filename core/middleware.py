from sqlalchemy.exc import IntegrityError
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from core.exceptions import BadRequestException, BaseAPIException
from core.settings import settings

# from starlette.types import Message


class ContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request.scope["context"] = (
            request.scope.get("aws.event", {})
            .get("requestContext", {})
            .get("authorizer", {})
        )
        return await call_next(request)


class CustomHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        if response.status_code == 303:
            response.headers["X-UI-TOAST"] = "false"
        elif response.status_code == 422:
            response.headers["X-UI-TOAST"] = "true"
        return response


class CustomExceptionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except IntegrityError as e:
            match request.method:
                case "POST":
                    action = "create"
                case "PATCH" | "PUT":
                    action = "update"
                case "DELETE":
                    action = "delete"
                case "GET":
                    action = "get"
                case _:
                    action = "action"
            raise BadRequestException(detail=f"Entity {action} failed: {e}")
        except BaseAPIException:
            raise
        except Exception as exc:
            raise BadRequestException(detail=str(exc))
