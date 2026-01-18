import warnings
import os
from PIL import Image
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

# 忽略无关警告
warnings.filterwarnings("ignore")

# 配置路径
model_path = "weights"  # 模型权重路径
image_dir = "cust-data/train"  # 图片文件夹路径
# 支持的图片格式
supported_formats = (".jpg", ".jpeg", ".png", ".bmp", ".tiff")

# 加载模型和处理器（只加载一次，提升效率）
processor = TrOCRProcessor.from_pretrained(model_path)
model = VisionEncoderDecoderModel.from_pretrained(model_path)

# 遍历文件夹下的所有图片文件
for filename in os.listdir(image_dir):
    # 过滤非图片文件
    if not filename.lower().endswith(supported_formats):
        continue
    
    # 拼接完整图片路径
    image_path = os.path.join(image_dir, filename)
    print(f"===== 处理图片: {filename} =====")
    
    try:
        # 读取并处理图片
        image = Image.open(image_path)
        image = image.convert("RGB")  # 统一转为RGB格式
        
        # OCR识别逻辑
        pixel_values = processor(images=image, return_tensors="pt").pixel_values
        generated_ids = model.generate(pixel_values, min_length=5)
        chat_content = processor.batch_decode(
            generated_ids, 
            skip_special_tokens=True, 
            clean_up_tokenization_spaces=True
        )[0]
        
        # 打印识别结果
        print(f"识别内容: {chat_content.strip()}\n")
    
    except Exception as e:
        print(f"处理图片 {filename} 时出错: {str(e)}\n")