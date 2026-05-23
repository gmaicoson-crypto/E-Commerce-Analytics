from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from database import engine, Base
from routers import (
    auth,
    system,
    sales,
    products,
    users,
    orders,
    finance,
    notifications,
    sse,
    notify,
    ingest,
)

# 启动时创建所有数据库表
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Application startup")
    yield
    print("Application shutdown")


app = FastAPI(
    title="E-Commerce Analytics API",
    description="Backend API for e-commerce data analysis platform",
    version="1.0.0",
    lifespan=lifespan,
)

# 跨域中间件，允许所有来源访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册各业务模块路由
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(system.router, prefix="/api/system", tags=["System"])
app.include_router(sales.router, prefix="/api/sales", tags=["Sales"])
app.include_router(products.router, prefix="/api/products", tags=["Products"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(orders.router, prefix="/api/orders", tags=["Orders"])
app.include_router(finance.router, prefix="/api/finance", tags=["Finance"])
app.include_router(
    notifications.router, prefix="/api/notifications", tags=["Notifications"]
)
app.include_router(sse.router, prefix="/api/sse", tags=["Streaming"])
app.include_router(notify.router, prefix="/api/notify", tags=["Notify"])
app.include_router(ingest.router, prefix="/api/ingest", tags=["Simulator Ingest"])


# 健康检查接口
@app.get("/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
