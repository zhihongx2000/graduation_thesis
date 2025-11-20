import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import pdf
from src.core.config import settings

def create_app():
    app = FastAPI(
        title="SOMA",
        version="0.0.1",
        description="SOMA: Smart Guardian of Substations."
    )

    # 1. 配置 CORS (允许前端跨域访问)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], # 开发环境允许所有，生产环境请指定域名
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. 挂载路由
    app.include_router(pdf.router, prefix="/api/v1")

    # 3. 挂载静态文件 (为将来访问解析后的图片做准备)
    # 访问: http://localhost:8000/static/artifacts/xxx.png
    app.mount("/static", StaticFiles(directory=settings.STORAGE_DIR), name="static")

    @app.get("/health")
    async def health_check():
        return {"status": "ok", "db_path": str(settings.DB_PATH)}

    return app

app = create_app()

if __name__ == "__main__":
    # 启动服务
    # 自动创建 storage 目录和 db
    print(f"Storage Path: {settings.STORAGE_DIR}")
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8001, 
        reload=True, 
        reload_dirs=["src"]  # <--- 只监控 src 文件夹下的变动
    )