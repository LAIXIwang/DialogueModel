"""统一业务异常与全局异常处理。"""

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class BizError(Exception):
    """业务异常：携带 HTTP 状态码与业务错误码。"""

    def __init__(self, message: str, status_code: int = 400, code: int = 4000):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


def ok(data=None, message: str = "success"):
    return {"code": 0, "message": message, "data": data}


async def biz_error_handler(_: Request, exc: BizError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message, "data": None},
    )


async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"code": 4220, "message": f"参数校验失败: {exc.errors()[:1]}", "data": None},
    )


async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
    import logging

    logging.getLogger("admin").exception("unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"code": 5000, "message": "服务内部错误", "data": None},
    )


def register_exception_handlers(app) -> None:
    app.add_exception_handler(BizError, biz_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
