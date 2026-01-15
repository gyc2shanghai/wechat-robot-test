import warnings
from PIL import Image
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
warnings.filterwarnings("ignore")

image = Image.open("chat_screenshot.png")
image = image.convert("RGB")
model_path = "hand-write"
processor = TrOCRProcessor.from_pretrained(model_path)
model = VisionEncoderDecoderModel.from_pretrained(model_path)
pixel_values = processor(images=image, return_tensors="pt").pixel_values
generated_ids = model.generate(pixel_values,min_length=10)
chat_content = processor.batch_decode(generated_ids, skip_special_tokens=True, clean_up_tokenization_spaces=True)[0]
print(chat_content.strip())