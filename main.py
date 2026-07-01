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
EXAM_ORIGIN = "https://iitm.ac.in"  # Added the IITM portal origin for verification

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ASSIGNED_ORIGIN, EXAM_ORIGIN],  # Strict matches, no wildcards
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

app.add_middleware(RateLimitMiddleware)

# -----------------------------------------------------------------------------
# ENDPOINT: GET /ping
# -----------------------------------------------------------------------------
@app.get("/ping")
async def ping(request: Request):
    request_id = getattr(request.state, "request_id", "unknown")
    return {
        "email": "24f3002070@ds.study.iitm.ac.in",  # Your verified student email
        "request_id": request_id
    }

