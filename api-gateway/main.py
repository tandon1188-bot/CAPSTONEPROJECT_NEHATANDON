from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
import httpx
import redis.asyncio as redis
from jose import jwt, JWTError
from datetime import datetime
import os

# Load environment variables
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
JWT_SECRET = os.getenv("JWT_SECRET", "your_jwt_secret")

# Microservice endpoints
MICROSERVICES = {
    "auth": "http://auth-service:8001",
    "books": "http://books-service:8002",
    "orders": "http://orders-service:8003",
    "reviews": "http://reviews-service:8004"
}

app = FastAPI(title="API Gateway")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Redis for rate limiting
@app.on_event("startup")
async def startup():
    r = redis.from_url(REDIS_URL, decode_responses=True)
    await FastAPILimiter.init(r)

# JWT Authentication Dependency
async def get_current_user(request: Request):
    token = request.headers.get("Authorization")
    if not token:
        return None  # Unauthenticated
    try:
        payload = jwt.decode(token.split(" ")[1], JWT_SECRET, algorithms=["HS256"])
        return payload  # Contains user info, e.g., role
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Health check endpoint
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "services": {name: "healthy" for name in MICROSERVICES},
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

# Generic route handler
@app.api_route("/api/v1/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(service: str, path: str, request: Request, user=Depends(get_current_user)):
    
    # Rate limiting logic
    if user is None:
        limiter = RateLimiter(times=20, seconds=60)  # Unauthenticated
    elif user.get("role") == "admin":
        limiter = RateLimiter(times=500, seconds=60)  # Admin
    else:
        limiter = RateLimiter(times=100, seconds=60)  # Authenticated

    await limiter(request)

    # Determine microservice
    service_url = MICROSERVICES.get(service)
    if not service_url:
        raise HTTPException(status_code=404, detail="Service not found")

    # Forward the request
    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                request.method,
                f"{service_url}/{path}",
                headers=request.headers.raw,
                content=await request.body()
            )
        except httpx.RequestError:
            raise HTTPException(status_code=502, detail="Service unavailable")

    # Logging
    print(f"{datetime.utcnow().isoformat()} - {request.client.host} - {request.method} /{service}/{path} -> {response.status_code}")

    return JSONResponse(content=response.json(), status_code=response.status_code)
