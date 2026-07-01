import time
import uuid
from collections import defaultdict
from fastapi import FastAPI, Request, Response
from starlette.datastructures import Headers

app = FastAPI()

# 1. State Store for tracking limits
RATE_LIMIT_DATA = defaultdict(list)
WINDOW_SECONDS = 10
MAX_REQUESTS = 14  

ASSIGNED_ORIGIN = "https://example.com"

@app.middleware("http")
async def combined_assignment_middleware(request: Request, call_next):
    # -------------------------------------------------------------------------
    # 1. HANDLE CORS PREFLIGHT (OPTIONS)
    # -------------------------------------------------------------------------
    origin = request.headers.get("origin")
    
    if request.method == "OPTIONS":
        response = Response(status_code=200)
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "X-Request-ID, X-Client-Id, Content-Type, Authorization"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response

    # -------------------------------------------------------------------------
    # 2. MIDDLEWARE 1: REQUEST CONTEXT
    # -------------------------------------------------------------------------
    request_id = request.headers.get("X-Request-ID")
    if not request_id:
        request_id = str(uuid.uuid4())
    
    request.state.request_id = request_id

    # -------------------------------------------------------------------------
    # 3. MIDDLEWARE 3: RATE LIMITER
    # -------------------------------------------------------------------------
    client_id = request.headers.get("X-Client-Id")
    if client_id:
        now = time.time()
        timestamps = RATE_LIMIT_DATA[client_id]
        
        while timestamps and now - timestamps[0] > WINDOW_SECONDS:
            timestamps.pop(0)
            
        if len(timestamps) >= MAX_REQUESTS:
            response = Response(content="Rate limit exceeded.", status_code=429)
            if origin:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["X-Request-ID"] = request_id
            return response
            
        timestamps.append(now)

    # -------------------------------------------------------------------------
    # 4. EXECUTE INNER APP & APPLY RESPONSE CORS HEADERS
    # -------------------------------------------------------------------------
    response = await call_next(request)
    
    # Inject Context Header
    response.headers["X-Request-ID"] = request_id
    
    # Inject Final CORS permissions dynamically
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        
    return response

# -----------------------------------------------------------------------------
# ENDPOINT: GET /ping
# -----------------------------------------------------------------------------
@app.get("/ping")
async def ping(request: Request):
    request_id = getattr(request.state, "request_id", "unknown")
    return {
        "email": "24f3002070@ds.study.iitm.ac.in",
        "request_id": request_id
    }
