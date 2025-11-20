"""
实现真实的文件保存逻辑。使用 shutil 高效地将上传流写入磁盘，
并使用 UUID 重命名文件（防止用户上传同名文件导致覆盖），同时在数据库中记录原始文件名：
/pdf/upload, /pdf/parse, /pdf/status
"""

import uuid
import shutil
import asyncio
from fastapi import APIRouter, UploadFile, HTTPException, BackgroundTasks, File, Form, Query, Body
from fastapi.responses import JSONResponse

from pydantic import BaseModel
from datetime import datetime
from typing import Literal

from ...core.config import settings
from ...dao.file_manager import file_manager
# from ...services.fileparse_service import mineru_parse_pdf_service
from src.services.fileparse_service.mineru_parse_pdf_service import parse_service

router = APIRouter(prefix="/pdf", tags=["PDF"])

@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    knowledge_name: str = Form("default_index"),
    replace: bool = Form(True)
): 
    # TODO: 后续计划扩展接口功能，可以接入 .doc , .docx , .xlsx 等类型文件
    # 1. 验证文件类型
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # 2. 生成唯一的文件ID和存储路径
    now = datetime.utcnow()
    date_str = now.strftime("%Y-%m-%d")          # 2025-11-14
    save_dir = settings.UPLOAD_DIR / date_str    # UPLOAD_DIR/2025-11-14
    save_dir.mkdir(parents=True, exist_ok=True)  # 自动创建

    file_id = f"f_{uuid.uuid4().hex[:8]}"
    safe_filename = f"{file_id}.pdf"
    save_path = save_dir / safe_filename         # 最终路径

    # 3. 物理保存文件
    try:
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File save failed: {str(e)}")

    # 4. 记录元数据到 SQLite
    file_manager.add_file(
        file_id=file_id,
        filename=file.filename,  # 原始文件名
        storage_path=str(save_path),
        index_name=knowledge_name
    )

    return {
        "fileId": file_id,
        "name": file.filename,
        "status": "idle",
        "knowledge_name": knowledge_name
    }

@router.get("/list")
async def list_index_files(knowledge_name: str = Query("default_index")):
    """
    获取指定知识库下的文件列表，否则默认获取全部知识库保存的文件
    """
    all_files = file_manager.list_index_files(index_name=knowledge_name)
    
    filtered_files = [f for f in all_files if f.get("index_name") == knowledge_name]
    
    return {
        "total": len(filtered_files),
        "files": filtered_files
    }

# 伪造的mineru解析方法
# async def fake_mineru_parse(file_id: str):
#     """模拟耗时解析"""
#     try:
#         # 0% -> 100% 模拟
#         for i in range(1, 6):
#             await asyncio.sleep(1) # 模拟耗时
#             file_manager.update_status(file_id, "parsing", progress=i*20)
        
#         # 完成
#         file_manager.update_status(file_id, "ready", progress=100)
#     except Exception as e:
#         file_manager.update_status(file_id, "error", error_msg=str(e))

class ParseRequest(BaseModel):
    fileId: str
    # 对应前端传来的 knowledge_name，默认值为 default_index
    knowledge_name: str = "default_index"
    parse_method: Literal["pipeline", "vlm-transformers"]

@router.post("/parse")
async def parse_pdf(
    payload: ParseRequest, # 使用 Pydantic 模型接收参数
    tasks: BackgroundTasks
):
    """
    触发解析，接入MinerU
    """
    file_id = payload.fileId
    index_name = payload.knowledge_name
    parse_method = payload.parse_method
    
    # 1. 检查文件是否存在 (需要传入 index_name)
    file_info = file_manager.get_file(file_id) 
    if not file_info:
        raise HTTPException(status_code=404, detail="File not found in this knowledge base")
    
    # 2. 检查是否已经在解析中
    if file_info["status"] == "parsing":
        return JSONResponse(status_code=202, content={"msg": "该文件正在解析中，请稍等..."})
    
    if file_info["status"] == "ready":
        return JSONResponse(status_code=202, content={"msg": "文件已经解析完成，无需重新解析!"})

    # 3. 更新状态
    file_manager.update_status(file_id, "parsing", progress=5)
    
    # 4. 启动真实解析任务
    # 假如后台任务出现任何报错，则重置文件状态为 error
    try:
        tasks.add_task(parse_service.run_parse, file_id)
    except: 
        file_manager.update_status(file_id, "error", progress=0)

    return JSONResponse(
        status_code=202, 
        content={"jobId": f"j_{uuid.uuid4().hex[:8]}", "msg": "Parsing job started"}
    )

@router.get("/status")
async def get_parse_status(
    fileId: str = Query(...), 
    knowledge_name: str = Query("default_index")
):
    """
    查询状态
    """
    # 查询数据库，获取文件信息
    file_info = file_manager.get_file(fileId) 
    
    if not file_info:
        raise HTTPException(status_code=404, detail="File not found")
    
    return {
        "status": file_info["status"],
        "progress": file_info["progress"],
        "errorMsg": file_info["error_msg"]
    }
