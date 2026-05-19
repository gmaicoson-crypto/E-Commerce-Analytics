from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio

from database import engine, Base
from routers import auth, system, sales, products, users, orders, finance, notifications, sse, notify

# Create all tables on startup
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Application startup")
    yield
    # Shutdown
    print("Application shutdown")


app = FastAPI(
    title="E-Commerce Analytics API",
    description="Backend API for e-commerce data analysis platform",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(system.router, prefix="/api/system", tags=["System"])
app.include_router(sales.router, prefix="/api/sales", tags=["Sales"])
app.include_router(products.router, prefix="/api/products", tags=["Products"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(orders.router, prefix="/api/orders", tags=["Orders"])
app.include_router(finance.router, prefix="/api/finance", tags=["Finance"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(sse.router, prefix="/api/sse", tags=["Streaming"])
app.include_router(notify.router, prefix="/api/notify", tags=["Notify"])

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
