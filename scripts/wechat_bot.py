import win32gui, win32con, win32api, win32clipboard, time
from ctypes import windll
from PIL import ImageGrab
from PIL import Image
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

windll.user32.SetProcessDPIAware()

# ===================== 核心配置（根据你的实际情况修改） =====================
# 1. 微信窗口标题关键词
WECHAT_WINDOW_TITLE_KEY = "微信"
# 2. 特征像素点（用之前的工具获取的坐标，替换成你的）
FEATURE_PIXELS = [(300, 600), (400, 700), (200, 500)]  # 相对微信窗口的偏移坐标
# 3. 目标关键词列表（从你的文档中提取）
TARGET_KEYWORDS = ["我的金币", "金币余额", "打工", "我要打工", "抢劫", "买彩票"]
# 4. 过滤配置
MAX_MESSAGE_LENGTH_PIXEL = 80  # 消息最大高度（像素），超过则判定为过长消息
MAX_TEXT_LENGTH = 20  # 消息最大文字长度，超过则过滤
COLOR_DIFF_THRESHOLD = 5  # 像素颜色差值阈值
NON_TEXT_COLOR_THRESHOLD = 10  # 非文字内容的颜色混乱度阈值

# ===================== 全局变量 =====================
LAST_PIXEL_COLORS = []  # 上一次的特征像素颜色
GLOBAL_WECHAT_RECT = None  # 微信窗口坐标 (左, 上, 右, 下)
GLOBAL_WECHAT_HANDLE = None


def get_wechat_handle_once():
    """获取微信句柄（全局只初始化1次，异常时重新获取）"""
    global GLOBAL_WECHAT_HANDLE, GLOBAL_WECHAT_RECT
    
    # 如果已有有效句柄，直接返回
    if GLOBAL_WECHAT_HANDLE and win32gui.IsWindow(GLOBAL_WECHAT_HANDLE):
        return GLOBAL_WECHAT_HANDLE
    
    # 重新获取句柄
    def callback(handle, extra):
        if win32gui.GetWindowText(handle).find("微信") != -1:
            extra.append(handle)
        return True
    handles = []
    win32gui.EnumWindows(callback, handles)
    
    if handles:
        GLOBAL_WECHAT_HANDLE = handles[0]
        GLOBAL_WECHAT_RECT = win32gui.GetWindowRect(GLOBAL_WECHAT_HANDLE)
        print(f"✅ 重新获取微信句柄：{GLOBAL_WECHAT_HANDLE}")
        return GLOBAL_WECHAT_HANDLE
    else:
        print("❌ 未找到微信窗口")
        return None



def get_pixel_color(hwnd, x, y):
    """读取指定窗口中相对坐标(x, y)处的像素颜色（低消耗）"""
    hdc = win32gui.GetDC(hwnd)  # 使用窗口句柄获取DC
    color = win32gui.GetPixel(hdc, x, y)  # 直接使用窗口相对坐标
    win32gui.ReleaseDC(hwnd, hdc)  # 释放窗口DC
    # 解析为RGB
    b = color & 0xFF
    g = (color >> 8) & 0xFF
    r = (color >> 16) & 0xFF
    return (r, g, b)

# ==========================
# 监听消息模块
# ==========================
def check_pixel_change():
    """检测特征像素点是否变化"""
    #global GLOBAL_WECHAT_RECT, LAST_PIXEL_COLORS
    if not GLOBAL_WECHAT_HANDLE:
        return
    if not GLOBAL_WECHAT_RECT:
        return 
    # 获取微信窗口
    wechat_handle = find_wechat()
    if not wechat_handle:
        print("⚠️ 未找到微信窗口")
        return False
    #GLOBAL_WECHAT_RECT = get_wechat_window_rect(wechat_handle)
    
    # 读取特征像素点颜色
    current_colors = []
    for (dx, dy) in FEATURE_PIXELS:
        x = GLOBAL_WECHAT_RECT[0] + dx
        y = GLOBAL_WECHAT_RECT[1] + dy
        current_colors.append(get_pixel_color(x, y))
    
    # 首次初始化
    if not LAST_PIXEL_COLORS:
        LAST_PIXEL_COLORS = current_colors
        return False
    
    # 判断像素是否变化
    has_change = False
    for i in range(len(current_colors)):
        r1, g1, b1 = LAST_PIXEL_COLORS[i]
        r2, g2, b2 = current_colors[i]
        diff = abs(r1-r2) + abs(g1-g2) + abs(b1-b2)
        if diff > COLOR_DIFF_THRESHOLD:
            has_change = True
            break
    
    LAST_PIXEL_COLORS = current_colors
    return has_change

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
    if not GLOBAL_WECHAT_HANDLE:
        return

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
        if not GLOBAL_WECHAT_RECT:
            return  
        left, top, right, bottom = GLOBAL_WECHAT_RECT                
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
        generated_ids = model.generate(pixel_values,min_length=5)
        
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
        get_wechat_handle_once()
        # 检查微信窗口是否可见，若不可见则恢复显示
        if not win32gui.IsWindowVisible(GLOBAL_WECHAT_HANDLE):
            win32gui.ShowWindow(GLOBAL_WECHAT_HANDLE, win32con.SW_RESTORE)        
        # 将微信窗口设置为前台窗口（激活窗口）
        win32gui.SetForegroundWindow(GLOBAL_WECHAT_HANDLE)
        # 等待0.5秒，确保窗口有足够时间响应激活操作
        time.sleep(0.5) 
         # 给窗口一些时间来响应
        # 捕获聊天区域截图
        screenshot_path = capture_chat_screenshot()
        print(f"截图保存路径: {screenshot_path}")
        
        # 使用OCR获取聊天内容
        # 加载TrOCR模型和处理器（在函数外加载，避免重复加载）
        model_path = "hand-write"
        processor = TrOCRProcessor.from_pretrained(model_path)
        model = VisionEncoderDecoderModel.from_pretrained(model_path)
        
        chat_msg = get_wechat_chat_msg_trocr()  
        print(chat_msg)
        
        # 发送测试消息
        #send_msg("我的金币")
        #send_msg("开始打工")
        #send_msg("买彩票")
        #send_msg("我要抢劫")
        #print("消息发送成功")
            
    except Exception as e:
        print(f"操作失败：{e}")