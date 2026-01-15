import win32gui, win32con, win32api, win32clipboard, time
from ctypes import windll
from PIL import ImageGrab
from PIL import Image
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

windll.user32.SetProcessDPIAware()

def find_wechat():
    """
    查找微信主窗口句柄
    
    返回:
        int: 微信窗口句柄，如果未找到则返回None
    """
    hwnd = None
    def cb(handle, _):
        nonlocal hwnd
        if "微信" in win32gui.GetWindowText(handle):
            hwnd = handle
            return False
        return True
    win32gui.EnumWindows(cb, None)
    return hwnd

# ==========================
# 发送消息模块
# ==========================
def send_msg(text):
    """
    向微信发送消息函数
    参数:
        text: 要发送的消息文本
    异常:
        当未找到微信窗口时抛出异常
    """
    # 查找微信主窗口句柄
    hwnd = find_wechat()
    # 如果未找到微信窗口，抛出异常
    if not hwnd: 
        raise Exception("未找到微信窗口")
    
    # 检查微信窗口是否可见，若不可见则恢复显示
    if not win32gui.IsWindowVisible(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    
    # 将微信窗口设置为前台窗口（激活窗口）
    win32gui.SetForegroundWindow(hwnd)
    # 等待0.5秒，确保窗口有足够时间响应激活操作
    time.sleep(0.5)  # 给窗口一些时间来响应
    
    # 打开剪贴板
    win32clipboard.OpenClipboard()
    # 清空剪贴板内容
    win32clipboard.EmptyClipboard()
    # 将消息文本设置到剪贴板（使用Unicode格式）
    win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
    # 关闭剪贴板
    win32clipboard.CloseClipboard()
    
    # 使用键盘模拟Ctrl+V粘贴操作
    win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)  # 按下Ctrl键
    win32api.keybd_event(ord('V'), 0, 0, 0)  # 按下V键
    win32api.keybd_event(ord('V'), 0, win32con.KEYEVENTF_KEYUP, 0)  # 释放V键
    win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)  # 释放Ctrl键
    
    # 使用键盘模拟Enter键发送消息
    win32api.keybd_event(win32con.VK_RETURN, 0, 0, 0)  # 按下Enter键
    win32api.keybd_event(win32con.VK_RETURN, 0, win32con.KEYEVENTF_KEYUP, 0)  # 释放Enter键

# ==========================
# 截图模块
# ==========================
def capture_chat_screenshot():
    """
    捕获微信聊天区域的截图
    
    返回:
        str: 截图保存路径，如果失败则返回错误信息
    """
    try:
        # 查找微信主窗口句柄
        hwnd = find_wechat()
        if not hwnd:
            return "未找到微信窗口"
        
        # 检查微信窗口是否可见，若不可见则恢复显示
        if not win32gui.IsWindowVisible(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        
        # 将微信窗口设置为前台窗口（激活窗口）
        win32gui.SetForegroundWindow(hwnd)
        # 等待0.5秒，确保窗口有足够时间响应激活操作
        time.sleep(0.5)  # 给窗口一些时间来响应
        
        # 获取微信窗口位置和大小
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        print(f"微信窗口坐标: {left}, {top}, {right}, {bottom}")
            
        # 调整聊天区域的坐标（根据实际微信界面调整这些参数）
        chat_left_offset = 440      # 左侧边距
        chat_top_offset = 325         # 顶部边距（标题栏和菜单栏高度）
        chat_right_offset = 30     # 右侧边距（滚动条宽度）
        chat_bottom_offset = 220    # 底部边距（输入框高度）
        
        # 计算聊天区域在窗口内的相对坐标
        chat_width = right - left - chat_left_offset - chat_right_offset
        chat_height = bottom - top - chat_top_offset - chat_bottom_offset
            
        print(f"聊天区域相对坐标: 左={chat_left_offset}, 上={chat_top_offset}, 宽={chat_width}, 高={chat_height}")        
 
        # 使用ImageGrab获取微信截图
        full_screenshot = ImageGrab.grab(bbox=(left, top, right, bottom))
            
        # 裁剪聊天区域
        chat_screenshot = full_screenshot.crop((chat_left_offset, chat_top_offset, 
                                              chat_left_offset + chat_width, 
                                              chat_top_offset + chat_height))
            
        # 保存截图以便调试（可选）
        screenshot_path = "chat_screenshot.png"
        chat_screenshot.save(screenshot_path)
        
        return screenshot_path
        
    except Exception as e:
        return f"截图失败: {str(e)}"


# ==========================
# trocr模块
# ==========================
def get_wechat_chat_msg_trocr():
    """
    使用TrOCR模型识别微信聊天内容的函数
    
    返回:
        str: 包含识别结果的字符串，如果成功则返回格式为"TrOCR识别的聊天内容:\n[识别文本]",
             如果失败则返回错误信息"TrOCR识别聊天内容失败: [错误详情]"
    """
    try:   
        # 从文件加载微信聊天区域截图
        image = Image.open("chat_screenshot.png")
        
        # 将图像转换为RGB格式（TrOCR模型要求的输入格式）
        image = image.convert("RGB")
        
        # 使用TrOCR处理器预处理图像，转换为模型可接受的像素值格式
        pixel_values = processor(images=image, return_tensors="pt").pixel_values
        
        # 将预处理后的图像输入模型，生成文本序列的ID
        generated_ids = model.generate(pixel_values)
        
        # 将生成的ID转换为可读文本，并跳过特殊标记
        chat_content = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        
        # 返回格式化的识别结果
        return f"TrOCR识别的聊天内容:\n{chat_content.strip()}"
    
    # 捕获所有可能的异常，确保函数不会崩溃
    except Exception as e:
        # 返回包含错误信息的字符串
        return f"TrOCR识别聊天内容失败: {str(e)}"


if __name__ == "__main__":
    try:
        # 捕获聊天区域截图
        screenshot_path = capture_chat_screenshot()
        print(f"截图保存路径: {screenshot_path}")
        
        # 使用OCR获取聊天内容
        # 加载TrOCR模型和处理器（在函数外加载，避免重复加载）
        model_path = "hand-write"
        processor = TrOCRProcessor.from_pretrained(model_path)
        model = VisionEncoderDecoderModel.from_pretrained(model_path)
        
        #chat_msg = get_wechat_chat_msg_trocr()  
        #print(chat_msg)
        
        # 发送测试消息
        #send_msg("我的金币")
        #send_msg("开始打工")
        #send_msg("买彩票")
        #send_msg("我要抢劫")
        #print("消息发送成功")
            
    except Exception as e:
        print(f"操作失败：{e}")