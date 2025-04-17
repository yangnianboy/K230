# 查找矩形示例
import time, os, gc, sys
from media.sensor import *
from media.display import *
from media.media import *

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

sensor = None
valid_corners = []
stable_rect = None
stable_corners = []
avg_cross_points = []
show_cross_flag = False

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

def camera_deinit():
    global sensor
    sensor.stop()
    Display.deinit()
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
    time.sleep_ms(100)
    MediaManager.deinit()

def euclid(p1, p2):
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return (dx*dx + dy*dy) ** 0.5

def is_valid_rect(corners, min_edge=30, max_ratio=1.8):
    lens = [euclid(corners[i], corners[(i+1)%4]) for i in range(4)]
    if any(l == 0 for l in lens):
        return False
    if not (0.85 < lens[0]/lens[2] < 1.15 and 0.85 < lens[1]/lens[3] < 1.15):
        return False
    long_edge, short_edge = max(lens[:2]), min(lens[:2])
    return long_edge > min_edge and short_edge > min_edge and long_edge/short_edge < max_ratio

def average_corners(all_corners):
    avg = [[0, 0] for _ in range(4)]
    n = len(all_corners)
    for corners in all_corners:
        for i, p in enumerate(corners):
            avg[i][0] += p[0]
            avg[i][1] += p[1]
    avg = [(x / n, y / n) for x, y in avg]
    left = sorted(avg[:2] + avg[2:], key=lambda p: p[0])[:2]
    right = sorted(avg[:2] + avg[2:], key=lambda p: p[0])[2:]
    tl, bl = sorted(left, key=lambda p: p[1])
    tr, br = sorted(right, key=lambda p: p[1])
    return [tl, tr, br, bl]

def offset_corners(corners, k=0.03):
    tl, tr, br, bl = corners
    def move(p_src, p_dst):
        dx = p_dst[0] - p_src[0]
        dy = p_dst[1] - p_src[1]
        return (round(p_src[0] + k * dx), round(p_src[1] + k * dy))
    new_tl = move(tl, br)
    new_tr = move(tr, bl)
    new_bl = move(bl, tr)
    new_br = move(br, tl)
    return [new_tl, new_tr, new_br, new_bl]

def capture_picture():
    global stable_rect, stable_corners, avg_cross_points, show_cross_flag

    fps = time.clock()
    while True:
        fps.tick()
        try:
            os.exitpoint()
            global sensor
            img = sensor.snapshot()
            Display.show_image(img,x=0,y=0,layer = Display.LAYER_OSD0)
            rects = img.find_rects(threshold=10000)
               
            for r in rects:
                corners = r.corners()
                if is_valid_rect(corners):
                    stable_rect = r.rect()
                    stable_corners = corners
                    valid_corners.append(corners)
                    break  # 只处理一个，减少抖动


            if stable_rect and rects:
                img.draw_rectangle(stable_rect, color=(255, 0, 0), thickness=2)
                for p in stable_corners:
                    img.draw_circle(p[0], p[1], 5, color=(0, 255, 0), thickness=2)


            if len(valid_corners) >= 5:
                avg = average_corners(valid_corners[:5])
                avg = offset_corners(avg, k=0.03)
                avg_cross_points = avg
                show_cross_flag = True
                valid_corners.clear()


            if show_cross_flag and rects:
                for x, y in avg_cross_points:
                    img.draw_cross(x, y, color=(255, 255, 0), size=8, thickness=2)
                    
            Display.show_image(img,x=DISPLAY_WIDTH-400,y=0,layer = Display.LAYER_OSD1)
            
            gc.collect()
            print(fps.fps())
        except KeyboardInterrupt as e:
            print("用户中断: ", e)
            break
        except BaseException as e:
            print(f"异常 {e}")
            break

def main():
    os.exitpoint(os.EXITPOINT_ENABLE)
    camera_is_init = False
    try:
        print("camera init")
        camera_init()
        camera_is_init = True
        print("camera capture")
        capture_picture()
    except Exception as e:
        print(f"异常 {e}")
    finally:
        if camera_is_init:
            print("camera deinit")
            camera_deinit()

if __name__ == "__main__":
    main()
