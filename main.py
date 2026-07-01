import time
import uuid
from collections import defaultdict
from fastapi import FastAPI, Request, Response

app = FastAPI()

# Memory tracking for client rate-limiting
RATE_LIMIT_DATA = defaultdict(list)
WINDOW_SECONDS = 10
MAX_REQUESTS = 14  

ASSIGNED_ORIGIN = "https://example.com"

@app.middleware("http")
async def absolute_assignment_middleware(request: Request, call_next):
    # Detect incoming origin header safely
    origin = request.headers.get("origin") or request.headers.get("Origin")
    
    # -------------------------------------------------------------------------
    # FAIL-SAFE CORS PREFLIGHT (OPTIONS) HANDLER
    # -------------------------------------------------------------------------
    if request.method == "OPTIONS":
        response = Response(status_code=200)
        # Fallback to wildcard '*' or current origin to guarantee preflight bypass
        response.headers["Access-Control-Allow-Origin"] = origin if origin else "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "X-Request-ID, X-Client-Id, Content-Type, Authorization"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response

    # -------------------------------------------------------------------------
    # MIDDLEWARE 1: REQUEST CONTEXT PROCESSING
    # -------------------------------------------------------------------------
    request_id = request.headers.get("X-Request-ID") or request.headers.get("x-request-id")
    if not request_id:
        request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    # -------------------------------------------------------------------------
    # MIDDLEWARE 3: PER-CLIENT RATE LIMITING FILTER
    # -------------------------------------------------------------------------
    client_id = request.headers.get("X-Client-Id") or request.headers.get("x-client-id")
    if client_id:
        now = time.time()
        timestamps = RATE_LIMIT_DATA[client_id]
        
        while timestamps and now - timestamps > WINDOW_SECONDS:
            timestamps.pop(0)
            
        if len(timestamps) >= MAX_REQUESTS:
            response = Response(content="Rate limit exceeded.", status_code=429)
            response.headers["X-Request-ID"] = request_id
            response.headers["x-request-id"] = request_id
            response.headers["Access-Control-Allow-Origin"] = origin if origin else "*"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            return response
            
        timestamps.append(now)

    # -------------------------------------------------------------------------
    # EXECUTE ENDPOINT LOGIC & APPLY ASSIGNED RESPONSE HEADERS
    # -------------------------------------------------------------------------
    response = await call_next(request)
    
    # Absolute injection rule: Deliver both uppercase and lowercase variants
    response.headers["X-Request-ID"] = request_id
    response.headers["x-request-id"] = request_id
    
    # Absolute CORS delivery: Guarantee headers attach even if origin is empty string
    response.headers["Access-Control-Allow-Origin"] = origin if origin else "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
        
    return response

# -----------------------------------------------------------------------------
# ENDPOINT: GET /ping 
# -----------------------------------------------------------------------------
@app.get("/ping")
async def ping(request: Request, response: Response):
    request_id = getattr(request.state, "request_id", "unknown")
    
    # Core system boundary injection
    response.headers["X-Request-ID"] = request_id
    response.headers["x-request-id"] = request_id
    
    return {
        "email": "24f3002070@ds.study.iitm.ac.in",
        "request_id": request_id
    }

