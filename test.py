import os
import base64
import mimetypes
from src.common import load_chat_model

vlm = load_chat_model("vllm:qwen3_vl")

print(f"实例化成功...")

def encode_image(image_path):
    """读取本地图片并转换为Base64 Data URI"""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")
        
    mime_type, _ = mimetypes.guess_type(image_path)
    if mime_type is None:
        mime_type = "image/png"
        
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        
    # 返回完整的 Data URI
    return f"data:{mime_type};base64,{encoded_string}"

image_data = encode_image("/nfs01/projects/50501482/s120242227094/graduation_thesis/mineru/test/合同页.png")
# print(image_data)

message = {
    "role": "user",
    "content": [
        {
            "type": "text",
            "text": "描述该图片，并说明是否存在印章:",
        },
        {
            "type": "image_url",
            "image_url":{
                "url": image_data,
            }
        },
    ],
}

response = vlm.invoke([message])

print(response)