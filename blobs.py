import time, os, gc
from media.sensor import Sensor
from media.display import Display
from media.media import MediaManager
from machine import FPIOA
from machine import UART

# ---------- 配置区 ----------
DISPLAY_MODE = "LCD"  # 可选值: "VIRT", "LCD", "HDMI"
DETECT_WIDTH  = 400  # 检测图像宽度
DETECT_HEIGHT = 240  # 检测图像高度
# 根据模式设置显示宽高
if DISPLAY_MODE == "VIRT":
    # 虚拟显示器模式
    DISPLAY_WIDTH = ALIGN_UP(1920, 16)
    DISPLAY_HEIGHT = 1080
elif DISPLAY_MODE == "LCD":
    # 3.1寸屏幕模式
    DISPLAY_WIDTH = 800
    DISPLAY_HEIGHT = 480
elif DISPLAY_MODE == "HDMI":
    # HDMI扩展板模式
    DISPLAY_WIDTH = 1920
    DISPLAY_HEIGHT = 1080
else:
    raise ValueError("未知的 DISPLAY_MODE，请选择 'VIRT', 'LCD' 或 'HDMI'")

# LAB 阈值 (L_min, L_max, A_min, A_max, B_min, B_max)
THRESHOLDS = {
    'red':   (20, 100,  25, 127, -128, 127),
    'green': ( 5,  91, -128, -33,   -7, 127),
}
# UART & FPIOA 配置
UART_ID       = UART.UART1
UART_BAUD     = 115200
UART_RX_PIN   = 18    # IO18 -> UART1_RX
UART_TX_PIN   = 16    # IO16 -> UART1_TX
# ----------------------------------

# 全局变量
sensor = None
uart   = None
recognize_red   = False
recognize_green = False

def camera_init():
    global sensor
    sensor = Sensor(width=1920, height=1080)
    sensor.reset()
    sensor.set_framesize(width=DETECT_WIDTH,height=DETECT_HEIGHT)
    sensor.set_pixformat(Sensor.RGB565)
    if DISPLAY_MODE == "VIRT":
        Display.init(Display.VIRT, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, fps=60,to_ide=True)
    elif DISPLAY_MODE == "LCD":
        Display.init(Display.ST7701, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
    elif DISPLAY_MODE == "HDMI":
        Display.init(Display.LT9611, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
    MediaManager.init()
    sensor.run()

def uart_init():
    global uart
    # 映射引脚
    fpioa = FPIOA()
    fpioa.set_function(UART_RX_PIN, FPIOA.UART1_RX)
    fpioa.set_function(UART_TX_PIN, FPIOA.UART1_TX)
    uart = UART(UART_ID, baudrate=UART_BAUD,bits=UART.EIGHTBITS, parity=UART.PARITY_NONE, stop=UART.STOPBITS_ONE, timeout=0)

def camera_deinit():
    global sensor
    sensor.stop()
    Display.deinit()
    MediaManager.deinit()
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
    time.sleep_ms(100)

def update_flags(cmd):
    """根据串口命令更新检测开关"""
    global recognize_red, recognize_green
    if cmd == ord('a'):         # 同时识别红、绿
        recognize_red   = True
        recognize_green = True
    elif cmd == ord('b'):       # 仅识别绿
        recognize_green = True
    elif cmd == ord('p'):       # 复位所有
        recognize_red   = False
        recognize_green = False

def detect_and_send(color_key, cmd_code, img):
    global uart
    """检测指定颜色最大 blob 并通过 UART 发送坐标"""
    thresh = THRESHOLDS[color_key]
    blobs = img.find_blobs([thresh],
                            pixels_threshold=10,
                            area_threshold=10,
                            merge=True)
    if not blobs:
        return
    # 取最大面积的 blob
    b = max(blobs, key=lambda b: b.area())
    # 绘制标记
    img.draw_rectangle(b.rect())
    img.draw_cross(b.cx(), b.cy())
    # 发送: [cmd, X, Y]
    uart.write(bytearray([cmd_code, b.cx() & 0xFF, b.cy() & 0xFF]))

def capture_loop():
    global sensor, uart
    fps = time.clock()
    while True:
        fps.tick()
        try:
            os.exitpoint()
            img = sensor.snapshot()
            # 显示原图
            Display.show_image(img, x=0, y=0, layer=Display.LAYER_OSD0)

            # 串口命令处理
            data = uart.read()
            if data:
                update_flags(data[0])

            # 颜色检测
            if recognize_red:
                detect_and_send('red',   0xAA, img)
            if recognize_green:
                detect_and_send('green', 0xAB, img)

            Display.show_image(img,
                               x=Display.width() - DETECT_WIDTH,
                               y=0,
                               layer=Display.LAYER_OSD1)

            gc.collect()
            print("FPS:", fps.fps())

        except KeyboardInterrupt:
            print("用户中断")
            break
        except Exception as e:
            print("异常:", e)
            break

def main():
    os.exitpoint(os.EXITPOINT_ENABLE)
    try:
        print("初始化摄像头和显示")
        camera_init()
        print("初始化 UART")
        uart_init()
        print("开始循环检测")
        capture_loop()
    finally:
        print("释放资源")
        camera_deinit()

if __name__ == "__main__":
    main()
