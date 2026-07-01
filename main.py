import time
import uuid
from collections import defaultdict
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI()

# -----------------------------------------------------------------------------
# MIDDLEWARE DEFINITIONS
# -----------------------------------------------------------------------------
class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())
        
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

RATE_LIMIT_DATA = defaultdict(list)
WINDOW_SECONDS = 10
MAX_REQUESTS = 14  

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)
            
        client_id = request.headers.get("X-Client-Id")
        if client_id:
            now = time.time()
            timestamps = RATE_LIMIT_DATA[client_id]
            
            while timestamps and now - timestamps > WINDOW_SECONDS:
                timestamps.pop(0)
                
            if len(timestamps) >= MAX_REQUESTS:
                return Response(
                    content="Rate limit exceeded.", 
                    status_code=429
                )
                
            timestamps.append(now)
            
        return await call_next(request)

# -----------------------------------------------------------------------------
# APPLICATION MIDDLEWARE REGISTRATION ORDER (CRUCIAL FIX)
# FastAPI runs middleware from the bottom up!
# -----------------------------------------------------------------------------

# 3. Runs LAST on the request (Inner Layer)
app.add_middleware(RequestContextMiddleware)

# 2. Runs SECOND on the request (Middle Layer)
app.add_middleware(RateLimitMiddleware)

# 1. Runs FIRST on the request (Outer Layer)
# This intercepts and responds to all CORS preflight OPTIONS requests immediately!
ASSIGNED_ORIGIN = "https://example.com"
EXAM_ORIGIN_1 = "https://iitm.ac.in"
EXAM_ORIGIN_2 = "http://iitm.ac.in"

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ASSIGNED_ORIGIN, EXAM_ORIGIN_1, EXAM_ORIGIN_2],
    allow_credentials=True,
    allow_methods=["*"],              
    allow_headers=["*"],              
)

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

