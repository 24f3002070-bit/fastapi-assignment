import time
import uuid
from collections import defaultdict
from fastapi import FastAPI, Request, Response

app = FastAPI()

# Memory tracking for client rate-limiting
RATE_LIMIT_DATA = defaultdict(list)
WINDOW_SECONDS = 10
MAX_REQUESTS = 14  

# -----------------------------------------------------------------------------
# COMBINED LAYERED MIDDLEWARE
# -----------------------------------------------------------------------------
@app.middleware("http")
async def combined_middleware_stack(request: Request, call_next):
    origin = request.headers.get("origin")
    
    # 1. Handle CORS Preflight Options immediately
    if request.method == "OPTIONS":
        response = Response(status_code=200)
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "X-Request-ID, X-Client-Id, Content-Type, Authorization"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response

    # 2. Layer 1: Request Context Processing
    request_id = request.headers.get("X-Request-ID")
    if not request_id:
        request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    # 3. Layer 3: Client Rate Limiting Filter
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

    # 4. Layer 2: Execute App Logic and Apply Dynamic Response Headers
    response = await call_next(request)
    
    # Guarantee header propagation on the response payload
    response.headers["X-Request-ID"] = request_id
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        
    return response

# -----------------------------------------------------------------------------
# ENDPOINT: GET /ping (Using dynamic Response container to guarantee header delivery)
# -----------------------------------------------------------------------------
@app.get("/ping")
async def ping(request: Request, response: Response):
    request_id = getattr(request.state, "request_id", "unknown")
    
    # Force add the header directly at the endpoint boundary 
    response.headers["X-Request-ID"] = request_id
    
    return {
        "email": "24f3002070@ds.study.iitm.ac.in",
        "request_id": request_id
    }
