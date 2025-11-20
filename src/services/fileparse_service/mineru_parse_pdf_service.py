import copy
import json
import os
from pathlib import Path

import asyncio
from loguru import logger

from langchain.chat_models import BaseChatModel
from typing import List,Union,Optional
from collections import defaultdict

from mineru.cli.common import convert_pdf_bytes_to_bytes_by_pypdfium2, prepare_env, read_fn
from mineru.data.data_reader_writer import FileBasedDataWriter
from mineru.utils.draw_bbox import draw_layout_bbox, draw_span_bbox
from mineru.utils.enum_class import MakeMode
from mineru.backend.vlm.vlm_analyze import doc_analyze as vlm_doc_analyze
from mineru.backend.pipeline.pipeline_analyze import doc_analyze as pipeline_doc_analyze
from mineru.backend.pipeline.pipeline_middle_json_mkcontent import union_make as pipeline_union_make
from mineru.backend.pipeline.model_json_to_middle_json import result_to_middle_json as pipeline_result_to_middle_json
from mineru.backend.vlm.vlm_middle_json_mkcontent import union_make as vlm_union_make
from mineru.utils.guess_suffix_or_lang import guess_suffix_by_path

from src.core.config import settings
from src.dao.file_manager import file_manager

def do_parse(
    output_dir,  # Output directory for storing parsing results
    pdf_file_names: list[str],  # List of PDF file names to be parsed
    pdf_bytes_list: list[bytes],  # List of PDF bytes to be parsed
    p_lang_list: list[str],  # List of languages for each PDF, default is 'ch' (Chinese)
    backend="pipeline",  # The backend for parsing PDF, default is 'pipeline'
    parse_method="auto",  # The method for parsing PDF, default is 'auto'
    formula_enable=True,  # Enable formula parsing
    table_enable=True,  # Enable table parsing
    server_url=None,  # Server URL for vlm-http-client backend
    f_draw_layout_bbox=True,  # Whether to draw layout bounding boxes
    f_draw_span_bbox=True,  # Whether to draw span bounding boxes
    f_dump_md=True,  # Whether to dump markdown files
    f_dump_middle_json=True,  # Whether to dump middle JSON files
    f_dump_model_output=True,  # Whether to dump model output files
    f_dump_orig_pdf=True,  # Whether to dump original PDF files
    f_dump_content_list=True,  # Whether to dump content list files
    f_make_md_mode=MakeMode.MM_MD,  # The mode for making markdown content, default is MM_MD
    start_page_id=0,  # Start page ID for parsing, default is 0
    end_page_id=None,  # End page ID for parsing, default is None (parse all pages until the end of the document)
):

    if backend == "pipeline":
        for idx, pdf_bytes in enumerate(pdf_bytes_list):
            new_pdf_bytes = convert_pdf_bytes_to_bytes_by_pypdfium2(pdf_bytes, start_page_id, end_page_id)
            pdf_bytes_list[idx] = new_pdf_bytes

        infer_results, all_image_lists, all_pdf_docs, lang_list, ocr_enabled_list = pipeline_doc_analyze(pdf_bytes_list, p_lang_list, parse_method=parse_method, formula_enable=formula_enable,table_enable=table_enable)

        for idx, model_list in enumerate(infer_results):
            model_json = copy.deepcopy(model_list)
            pdf_file_name = pdf_file_names[idx]
            local_image_dir, local_md_dir = prepare_env(output_dir, pdf_file_name, parse_method)
            image_writer, md_writer = FileBasedDataWriter(local_image_dir), FileBasedDataWriter(local_md_dir)

            images_list = all_image_lists[idx]
            pdf_doc = all_pdf_docs[idx]
            _lang = lang_list[idx]
            _ocr_enable = ocr_enabled_list[idx]
            middle_json = pipeline_result_to_middle_json(model_list, images_list, pdf_doc, image_writer, _lang, _ocr_enable, formula_enable)

            pdf_info = middle_json["pdf_info"]

            pdf_bytes = pdf_bytes_list[idx]
            _process_output(
                pdf_info, pdf_bytes, pdf_file_name, local_md_dir, local_image_dir,
                md_writer, f_draw_layout_bbox, f_draw_span_bbox, f_dump_orig_pdf,
                f_dump_md, f_dump_content_list, f_dump_middle_json, f_dump_model_output,
                f_make_md_mode, middle_json, model_json, is_pipeline=True
            )
    else:
        if backend.startswith("vlm-"):
            backend = backend[4:]

        f_draw_span_bbox = False
        parse_method = "vlm"
        for idx, pdf_bytes in enumerate(pdf_bytes_list):
            pdf_file_name = pdf_file_names[idx]
            pdf_bytes = convert_pdf_bytes_to_bytes_by_pypdfium2(pdf_bytes, start_page_id, end_page_id)
            local_image_dir, local_md_dir = prepare_env(output_dir, pdf_file_name, parse_method)
            image_writer, md_writer = FileBasedDataWriter(local_image_dir), FileBasedDataWriter(local_md_dir)
            middle_json, infer_result = vlm_doc_analyze(pdf_bytes, image_writer=image_writer, backend=backend, server_url=server_url)

            pdf_info = middle_json["pdf_info"]

            _process_output(
                pdf_info, pdf_bytes, pdf_file_name, local_md_dir, local_image_dir,
                md_writer, f_draw_layout_bbox, f_draw_span_bbox, f_dump_orig_pdf,
                f_dump_md, f_dump_content_list, f_dump_middle_json, f_dump_model_output,
                f_make_md_mode, middle_json, infer_result, is_pipeline=False
            )


def _process_output(
        pdf_info,
        pdf_bytes,
        pdf_file_name,
        local_md_dir,
        local_image_dir,
        md_writer,
        f_draw_layout_bbox,
        f_draw_span_bbox,
        f_dump_orig_pdf,
        f_dump_md,
        f_dump_content_list,
        f_dump_middle_json,
        f_dump_model_output,
        f_make_md_mode,
        middle_json,
        model_output=None,
        is_pipeline=True
):
    """处理输出文件"""
    if f_draw_layout_bbox:
        draw_layout_bbox(pdf_info, pdf_bytes, local_md_dir, f"{pdf_file_name}_layout.pdf")

    if f_draw_span_bbox:
        draw_span_bbox(pdf_info, pdf_bytes, local_md_dir, f"{pdf_file_name}_span.pdf")

    if f_dump_orig_pdf:
        md_writer.write(
            f"{pdf_file_name}_origin.pdf",
            pdf_bytes,
        )

    image_dir = str(os.path.basename(local_image_dir))

    if f_dump_md:
        make_func = pipeline_union_make if is_pipeline else vlm_union_make
        md_content_str = make_func(pdf_info, f_make_md_mode, image_dir)
        md_writer.write_string(
            f"{pdf_file_name}.md",
            md_content_str,
        )

    if f_dump_content_list:
        make_func = pipeline_union_make if is_pipeline else vlm_union_make
        content_list = make_func(pdf_info, MakeMode.CONTENT_LIST, image_dir)
        md_writer.write_string(
            f"{pdf_file_name}_content_list.json",
            json.dumps(content_list, ensure_ascii=False, indent=4),
        )

    if f_dump_middle_json:
        md_writer.write_string(
            f"{pdf_file_name}_middle.json",
            json.dumps(middle_json, ensure_ascii=False, indent=4),
        )

    if f_dump_model_output:
        md_writer.write_string(
            f"{pdf_file_name}_model.json",
            json.dumps(model_output, ensure_ascii=False, indent=4),
        )

    logger.info(f"local output dir is {local_md_dir}")


def group_by_page(content_list):
    """
    根据 page_idx 将内容分组
    """
    pages = defaultdict(list)
    for item in content_list:
        page_idx = item.get('page_idx', 0)
        pages[page_idx].append(item)
    return dict(pages)


def item_to_markdown(item, enable_image_caption=False, vlm: BaseChatModel = None):
    """
    使用 langchain 接入 VLM 完成图片 caption 补全。
    若 enable_image_caption=True 且 caption 缺失，则自动调用视觉模型生成 caption。

    item: content_list.json 中的每个对象，根据 type 分别处理
    enable_image_caption: 是否启用多模态视觉分析
    vlm: 可选，LangChain BaseChatModel 类型，大模型如 Qwen3-VL 的接口对象
    """
    import os

    # 处理文本
    if item['type'] == 'text':
        level = item.get('text_level', 0)
        text = item.get('text', '')

        if level == 1:
            return f"# {text}\n\n"
        elif level == 2:
            return f"## {text}\n\n"
        elif level == 3:
            return f"### {text}\n\n"
        elif level == 4:
            return f"#### {text}\n\n"
        elif level == 5:
            return f"##### {text}\n\n"
        else:
            return f"{text}\n\n"

    # 处理表格
    elif item['type'] == 'table':
        captions = item.get('table_caption', [])
        caption = captions[0] if captions else ''
        table_html = item.get('table_body', '')
        img_path = item.get('img_path', '')

        md = ""
        if caption:
            md += f"**{caption}**\n"
        if img_path:
            md += f"![{caption}]({img_path})\n"
        md += f"{table_html}\n\n"

        return md

    # 处理图片
    elif item['type'] == 'image':
        captions = item.get('image_caption', [])
        caption = captions[0] if captions else ''
        img_path = item.get('img_path', '')

        # 若 caption 缺失，且允许多模态分析
        if enable_image_caption and not caption and img_path and os.path.exists(img_path):

            # 若用户未传入模型，则加载默认本地 VLM
            if vlm is None:
                from .utils import load_chat_model
                vlm = load_chat_model("vllm:qwen3_vl")

            try:
                # LangChain 的 multimodal 输入，传入 image + prompt
                prompt = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": f"file://{img_path}"},
                            {"type": "text", "text": "请为这张图片生成简要的说明文字。"}
                        ]
                    }
                ]

                resp = vlm.invoke(prompt)
                new_caption = resp.content.strip() if hasattr(resp, "content") else ""

                if new_caption:
                    # 写回 item
                    item['image_caption'] = [new_caption]
                    caption = new_caption

            except Exception as e:
                # 捕获错误避免影响主流程
                print(f"[WARN] 图片 caption 生成失败: {img_path}, 错误: {e}")

        # Markdown 组装
        md = ""
        if caption:
            md += f"**{caption}**\n"
        if img_path:
            md += f"![{caption}]({img_path})\n\n"

        return md

    else:
        # 未定义类型直接返回空
        return "\n"

def assemble_pages_to_markdown(pages, enable_image_caption=True, vlm: BaseChatModel | None = None):
    """
    按页码组装所有项的Markdown，支持传递图片说明补全参数
    
    Args:
        pages: group_by_page返回的按页结构化数据（{page_idx: [item1, item2, ...]}）
        enable_image_caption: 是否启用图片说明自动补全，默认True
        vlm: 用于图片说明补全的LangChain BaseChatModel，默认None
    """
    page_md = {}
    for page_idx in sorted(pages.keys()):
        md = ''
        for item in pages[page_idx]:
            # 传递参数给item_to_markdown，支持图片说明补全控制
            md += item_to_markdown(item, enable_image_caption=enable_image_caption, vlm=vlm)
        page_md[page_idx] = md
    return page_md


def pipeline_pdf_to_md(
    doc_path: str,
    output_dir: str,
    file_name_prefix: str,
    lang: str = "ch",
    backend: str = "pipeline",
    enable_image_caption: bool = False,
    vlm: Optional[BaseChatModel] = None
):
    """
    串联 Mineru 解析与自定义 Markdown 生成逻辑
    Args:
        doc_path: PDF 文件路径
        output_dir: 输出根目录
        file_name_prefix: 输出文件名的前缀 (通常是 file_id，用于确保路径安全)
        lang: 语言
        backend: 解析后端 (pipeLine/vlm-transformers)
        enable_image_caption: 是否启用图片说明
        vlm: 视觉模型实例
    """
    doc_path = Path(doc_path)
    output_dir = Path(output_dir)
    
    if not doc_path.exists():
        raise FileNotFoundError(f"Input file not found: {doc_path}")

    logger.info(f"Processing PDF: {doc_path} -> {output_dir} (Prefix: {file_name_prefix})")

    # 1. 读取 PDF 二进制数据
    pdf_bytes = read_fn(str(doc_path))

    # 2. 调用 Mineru do_parse 执行核心解析
    # do_parse 是批量接口，我们需要封装成 list 传入
    do_parse(
        output_dir=str(output_dir),
        pdf_file_names=[file_name_prefix], # 强制使用 file_name_prefix (file_id) 作为目录名
        pdf_bytes_list=[pdf_bytes],
        p_lang_list=[lang],
        backend=backend,
        f_draw_layout_bbox=True,  # Whether to draw layout bounding boxes
        f_draw_span_bbox=False,  # Whether to draw span bounding boxes
        f_dump_md=False,  # Whether to dump markdown files
        f_dump_middle_json=False,  # Whether to dump middle JSON files
        f_dump_model_output=False,  # Whether to dump model output files
        f_dump_orig_pdf=False,  # Whether to dump original PDF files
    )

    # 3. 定位生成的 content_list.json
    # Mineru 的目录结构通常是: {output_dir}/{file_name_prefix}/{parse_method}/{file_name_prefix}_content_list.json
    target_dir = output_dir / file_name_prefix
    content_list_path = None
    
    # 寻找具体的子目录 (auto, ocr, txt)
    if target_dir.exists():
        for subdir in target_dir.iterdir():
            if subdir.is_dir():
                possible_path = subdir / f"{file_name_prefix}_content_list.json"
                if possible_path.exists():
                    content_list_path = possible_path
                    break
    
    if not content_list_path:
        raise FileNotFoundError(f"Failed to locate content_list.json in {target_dir}")

    logger.info(f"Found content list: {content_list_path}")

    # 4. 加载结构化数据
    with open(content_list_path, "r", encoding="utf-8") as f:
        content_list = json.load(f)

    # 5. 自定义后处理 (生成 Page JSON 和 Markdown)
    pages_struct = group_by_page(content_list)
    
    # 保存按页的 JSON
    page_json_path = content_list_path.parent / f"{file_name_prefix}_page_content.json"
    with open(page_json_path, "w", encoding="utf-8") as f:
        json.dump(pages_struct, f, ensure_ascii=False, indent=4)

    # 生成完整 Markdown
    page_md_dict = assemble_pages_to_markdown(pages_struct, enable_image_caption=enable_image_caption, vlm=vlm)
    
    full_md = ""
    for page_idx in sorted(page_md_dict.keys()):
        full_md += f"==== 第 {page_idx + 1} 页 ====\n\n"
        full_md += page_md_dict[page_idx]
        full_md += "\n---\n\n"
    
    # 保存 Markdown
    md_path = content_list_path.parent / f"{file_name_prefix}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(full_md)
    
    # 复制一份为 output.md 方便统一读取
    output_md_path = content_list_path.parent / "output.md"
    with open(output_md_path, "w", encoding="utf-8") as f:
        f.write(full_md)

    logger.success(f"Successfully generated MD: {md_path}")
    return str(output_md_path)


# 定义解析类，供 api 调用
class PdfParseService:
    def __init__(self):
        self.parse_method = "pipeline" # 默认采用pipeline方法解析pdf
        self.output_dir = settings.ARTIFACT_DIR
        self.enable_image_caption = False # 是否启用vlm模型对图片信息进行描述
    
    async def run_parse(self, file_id: str):
        # 1. 获取文件信息
        try:
            file_info = file_manager.get_file(file_id)
            file_name = file_info["filename"]
            if not file_name:
                logger.info(f"未找到文件：{file_name}")

            logger.info(f"开始解析文件：{file_name}")

            # 2. 获取文件存储地址
            file_path = file_info["storage_path"]
            safe_name = file_id
            output_dir = str(self.output_dir)

            file_manager.update_status(file_id, "parsing", progress=10)

            # 3. 进行文件解析
            doc_path_list = [file_path]
            # 2. 在线程池中执行耗时的解析任务
            # Mineru 是同步代码，必须 wrap 在 to_thread 中，否则会阻塞 FastAPI
            logger.info(f"Starting Mineru pipeline for {file_id}...")
            
            await asyncio.to_thread(
                pipeline_pdf_to_md,
                doc_path=file_path,
                output_dir=output_dir,
                file_name_prefix=safe_name,
                lang="ch",
                backend=self.parse_method,
                enable_image_caption=self.enable_image_caption,
                vlm=None # 暂时不传入 VLM 实例，如果有需要可以在这里初始化
            )
            
            # 3. 更新数据库状态 -> ready
            file_manager.update_status(file_id, "ready", progress=100)
            logger.success(f"[Task Done] File {file_id} parsed successfully.")

        except Exception as e:
            logger.error(f"[Task Error] {file_id}: {traceback.format_exc()}")
            file_manager.update_status(file_id, "error", error_msg=str(e))


# 单例实例
parse_service = PdfParseService()
        
if __name__ == '__main__':
    
    """To enable VLM mode, change the backend to 'vlm-xxx'"""
    # parse_doc(doc_path_list, output_dir, backend="vlm-transformers")  # more general.
    # parse_doc(doc_path_list, output_dir, backend="vlm-mlx-engine")  # faster than transformers in macOS 13.5+.
    # parse_doc(doc_path_list, output_dir, backend="vlm-vllm-engine")  # faster(engine).
    # parse_doc(doc_path_list, output_dir, backend="vlm-http-client", server_url="http://127.0.0.1:30000")  # faster(client).