import time
import logging
from fastapi import Request
from starlette.middleware.base import RequestResponseEndpoint


logger = logging.getLogger("app")


async def log_middleware(request: Request, call_next: RequestResponseEndpoint):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    log_dict = {
        "url": request.url.path,
        "method": request.method,
        "process_time": process_time,
    }
    logger.info(log_dict, extra=log_dict)
    return response
