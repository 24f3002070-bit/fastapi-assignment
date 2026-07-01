import time
import uuid
from collections import defaultdict
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI()

# Memory tracking for client rate-limiting
RATE_LIMIT_DATA = defaultdict(list)
WINDOW_SECONDS = 10
MAX_REQUESTS = 14  
ASSIGNED_ORIGIN = "https://example.com"

# -----------------------------------------------------------------------------
# SINGLE MONOLITHIC FAIL-SAFE MIDDLEWARE (Handles Context, CORS, and Rate-Limiter)
# -----------------------------------------------------------------------------
class AbsoluteAssignmentMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Grab incoming context metadata
        origin = request.headers.get("origin") or request.headers.get("Origin") or "*"
        
        # Read X-Request-ID case-insensitively
        request_id = request.headers.get("X-Request-ID") or request.headers.get("x-request-id")
        if not request_id:
            request_id = str(uuid.uuid4())
            
        request.state.request_id = request_id

        # 2. IMMEDIATE CORS PREFLIGHT (OPTIONS) BYPASS
        if request.method == "OPTIONS":
            response = Response(status_code=200)
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "X-Request-ID, X-Client-Id, Content-Type, Authorization"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            return response

        # 3. PER-CLIENT RATE LIMITING LAYER
        client_id = request.headers.get("X-Client-Id") or request.headers.get("x-client-id")
        if client_id:
            now = time.time()
            timestamps = RATE_LIMIT_DATA[client_id]
            
            while timestamps and now - timestamps > WINDOW_SECONDS:
                timestamps.pop(0)
                
            if len(timestamps) >= MAX_REQUESTS:
                # Custom block response that retains both CORS and Context tracking rules
                response = Response(content="Rate limit exceeded.", status_code=429)
                response.headers["X-Request-ID"] = request_id
                response.headers["x-request-id"] = request_id
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Expose-Headers"] = "X-Request-ID, x-request-id"
                return response
                
            timestamps.append(now)

        # 4. EXECUTE APP ROUTE LAYER
        response = await call_next(request)
        
        # 5. ABSOLUTE INJECTION RULE (Bakes both headers into the network message)
        response.headers["X-Request-ID"] = request_id
        response.headers["x-request-id"] = request_id
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Expose-Headers"] = "X-Request-ID, x-request-id"
        
        return response

# Register our single, multi-layer bulletproof controller
app.add_middleware(AbsoluteAssignmentMiddleware)

# -----------------------------------------------------------------------------
# ENDPOINT: GET /ping
# -----------------------------------------------------------------------------
@app.get("/ping")
async def ping(request: Request, response: Response):
    request_id = getattr(request.state, "request_id", "unknown")
    
    # Extra backup injection boundary
    response.headers["X-Request-ID"] = request_id
    response.headers["x-request-id"] = request_id
    
    return {
        "email": "24f3002070@ds.study.iitm.ac.in",
        "request_id": request_id
    }

