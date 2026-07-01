import time
import uuid
from collections import defaultdict
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI()

# -----------------------------------------------------------------------------
# MIDDLEWARE 1: Request Context
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

app.add_middleware(RequestContextMiddleware)

# -----------------------------------------------------------------------------
# MIDDLEWARE 2: CORS Configuration
# -----------------------------------------------------------------------------
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
# MIDDLEWARE 3: Per-Client Rate Limiting
# -----------------------------------------------------------------------------
RATE_LIMIT_DATA = defaultdict(list)
WINDOW_SECONDS = 10
MAX_REQUESTS = 14  

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # CRUCIAL FIX: Let browser preflight checks pass without rate limiting
        if request.method == "OPTIONS":
            response = await call_next(request)
            return response
            
        client_id = request.headers.get("X-Client-Id")
        if client_id:
            now = time.time()
            timestamps = RATE_LIMIT_DATA[client_id]
            
            while timestamps and now - timestamps > WINDOW_SECONDS:
                timestamps.pop(0)
                
            if len(timestamps) >= MAX_REQUESTS:
                # Add CORS headers directly onto the error block so browser permits reading 429
                error_response = Response(content="Rate limit exceeded.", status_code=429)
                origin = request.headers.get("origin")
                if origin in [ASSIGNED_ORIGIN, EXAM_ORIGIN_1, EXAM_ORIGIN_2]:
                    error_response.headers["Access-Control-Allow-Origin"] = origin
                return error_response
                
            timestamps.append(now)
            
        return await call_next(request)

app.add_middleware(RateLimitMiddleware)

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

