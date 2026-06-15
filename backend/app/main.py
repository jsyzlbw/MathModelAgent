"""MathModelAgent 应用入口，配置 FastAPI 应用和中间件。"""

from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
import os
from app.routers import (
    artifacts_router,
    common_router,
    config_router,
    files_router,
    gui_workspace_router,
    modeling_router,
    planning_router,
    rag_router,
    ws_router,
)
from app.utils.log_util import logger
from fastapi.staticfiles import StaticFiles
from app.utils.cli import get_ascii_banner, center_cli_str


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(get_ascii_banner())
    print(center_cli_str("GitHub:https://github.com/jihe520/MathModelAgent"))
    logger.info("Starting MathModelAgent")

    PROJECT_FOLDER = "./project"
    os.makedirs(PROJECT_FOLDER, exist_ok=True)

    yield
    logger.info("Stopping MathModelAgent")


app = FastAPI(
    title="MathModelAgent",
    description="Agents for MathModel",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(modeling_router.router)
app.include_router(ws_router.router)
app.include_router(common_router.router)
app.include_router(files_router.router)
app.include_router(config_router.router, prefix="/api/gui")
app.include_router(gui_workspace_router.router, prefix="/api/gui")
app.include_router(artifacts_router.router, prefix="/api/gui")
app.include_router(rag_router.router, prefix="/api/gui/rag")
app.include_router(planning_router.router, prefix="/api/gui")


# 跨域 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],  # 暴露所有响应头
)

app.mount(
    "/static",  # 这是访问时的前缀
    StaticFiles(directory="project/work_dir"),  # 这是本地文件夹路径
    name="static",
)
