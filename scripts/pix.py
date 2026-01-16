import pyautogui
import keyboard  

def get_pixel_position():
    """
    像素点坐标获取工具：
    - 运行后，移动鼠标到目标位置
    - 按F1键：获取当前鼠标坐标和像素颜色
    - 按ESC键：退出工具
    """
    print("=== 微信特征像素点获取工具 ===")
    print("操作说明：")
    print("1. 移动鼠标到想要监测的像素点位置")
    print("2. 按F1键：记录当前坐标和像素颜色")
    print("3. 按ESC键：退出工具")
    print("-" * 30)

    try:
        while True:
            # 监听F1键（获取坐标）
            if keyboard.is_pressed('f1'):
                # 获取当前鼠标坐标
                x, y = pyautogui.position()
                # 获取当前像素颜色（RGB）
                pixel_color = pyautogui.pixel(x, y)
                # 输出结果
                print(f"✅ 已记录：坐标(x={x}, y={y}) | 像素颜色(R={pixel_color[0]}, G={pixel_color[1]}, B={pixel_color[2]})")
                # 短暂延时，避免重复触发
                pyautogui.sleep(0.5)
            
            # 监听ESC键（退出）
            if keyboard.is_pressed('esc'):
                print("\n🔚 工具已退出")
                break

            # 降低CPU占用
            pyautogui.sleep(0.1)

    except Exception as e:
        print(f"工具出错：{e}")
    finally:
        # 释放键盘监听
        keyboard.unhook_all()

if __name__ == "__main__":
    # 注意：Windows系统可能需要以管理员身份运行，否则keyboard库可能无法监听快捷键
    get_pixel_position()