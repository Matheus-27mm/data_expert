"""Operational logs deliberately exclude credentials, bodies and query strings."""
import json
import logging
import time
from uuid import uuid4
from fastapi import Request
from fastapi.responses import JSONResponse

logger=logging.getLogger('uvicorn.error')

async def request_log(request:Request,call_next):
    request_id=str(uuid4())
    started=time.monotonic()
    try:
        response=await call_next(request)
    except Exception:
        # Avoid raw exception messages that can contain SQL values or connection strings.
        response=JSONResponse({'detail':'Erro interno. Tente novamente.','request_id':request_id},status_code=500)
    response.headers['X-Request-ID']=request_id
    route=request.scope.get('route')
    logger.info(json.dumps({'request_id':request_id,'method':request.method,
        'route':getattr(route,'path','unmatched'),'status':response.status_code,
        'duration_ms':round((time.monotonic()-started)*1000,1)}))
    return response
