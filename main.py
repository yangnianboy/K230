# 查找矩形示例
#
# 本示例展示了如何使用 April Tags 代码中的四元检测算法在图像中查找矩形。
# 四元检测算法以极其鲁棒的方式检测矩形，比基于 Hough 变换的方法更好。
# 例如，即使镜头畸变导致这些矩形看起来弯曲，它仍然可以检测到矩形。
# 圆角矩形也不是问题！（但由于这个特性，代码也会检测到小半径的圆）...
import time, os, gc, sys

from media.sensor import *
from media.display import *
from media.media import *

DETECT_WIDTH = ALIGN_UP(320, 16)
DETECT_HEIGHT = 240

sensor = None

def camera_init():
    global sensor

    # 构造一个默认配置的 Sensor 对象
    sensor = Sensor(width=DETECT_WIDTH,height=DETECT_HEIGHT)
    # 传感器复位
    sensor.reset()
    # 设置水平镜像
    # sensor.set_hmirror(False)
    # 设置垂直翻转
    # sensor.set_vflip(False)
    # 设置 chn0 输出尺寸
    sensor.set_framesize(width=DETECT_WIDTH,height=DETECT_HEIGHT)
    # 设置 chn0 输出格式
    sensor.set_pixformat(Sensor.RGB565)

    # 使用 IDE 作为显示输出
    Display.init(Display.VIRT, width= DETECT_WIDTH, height = DETECT_HEIGHT,fps=100,to_ide = True)
    # 初始化媒体管理器
    MediaManager.init()
    # 启动传感器
    sensor.run()

def camera_deinit():
    global sensor
    # 停止传感器
    sensor.stop()
    # 释放显示
    Display.deinit()
    # 进入休眠
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
    time.sleep_ms(100)
    # 释放媒体缓冲区
    MediaManager.deinit()

def euclid(p1, p2):
    """计算两点间欧氏距离"""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return (dx*dx + dy*dy) ** 0.5

def is_valid_rect(corners, min_edge=25, max_ratio=2):
    """根据边长和长宽比判断矩形是否“正常”"""
    # 取顺时针的四边长
    lens = [euclid(corners[i], corners[(i+1)%4]) for i in range(4)]
    # 任意一条边为 0 或者对边比例偏离太大都判为异常
    if any(l == 0 for l in lens):
        return False
    if not (0.85 < lens[0]/lens[2] < 1.15 and 0.85 < lens[1]/lens[3] < 1.15):
        return False
    long_edge, short_edge = max(lens[:2]), min(lens[:2])
    return long_edge > min_edge and short_edge > min_edge and long_edge/short_edge < max_ratio

def average_corners(all_corners):
    """对多帧检测到的角点取平均，并按顺时针 tl, tr, br, bl 排序"""
    # all_corners: list of 4-tuples，each is corners from one detection
    # 1. 均值
    avg = [ [0,0] for _ in range(4) ]
    n = len(all_corners)
    for corners in all_corners:
        for i, p in enumerate(corners):
            avg[i][0] += p[0]
            avg[i][1] += p[1]
    avg = [ (x/n, y/n) for x,y in avg ]
    # 2. 排序：先按 x 分左右，再按 y 分上下
    left  = sorted(avg[:2] + avg[2:], key=lambda p: p[0])[:2]
    right = sorted(avg[:2] + avg[2:], key=lambda p: p[0])[2:]
    tl, bl = sorted(left,  key=lambda p: p[1])
    tr, br = sorted(right, key=lambda p: p[1])
    return [tl, tr, br, bl]

def offset_corners(corners, k=0.03):
    """在平均框的基础上往内偏移 k 比例"""
    tl, tr, br, bl = corners
    # 对角线向内偏移
    def move(p_src, p_dst):
        dx = p_dst[0] - p_src[0]
        dy = p_dst[1] - p_src[1]
        return (round(p_src[0] + k*dx), round(p_src[1] + k*dy))
    new_tl = move(tl, br)
    new_tr = move(tr, bl)
    new_bl = move(bl, tr)
    new_br = move(br, tl)
    return [new_tl, new_tr, new_br, new_bl]

def capture_picture():
    fps = time.clock()
    while True:
        fps.tick()
        try:
            os.exitpoint()
            global sensor
            img = sensor.snapshot()

            # 下面的 `threshold` 应设置为足够高的值，以过滤掉噪声
            # 图像中检测到的低边缘幅值的矩形。矩形越大、对比度越高，边缘幅值越大...

            rects = img.find_rects(threshold=10000)
            valid_corners = []
            for r in rects:
                corners = r.corners()
                if is_valid_rect(corners):
                    # 画矩形与角点
                    img.draw_rectangle(r.rect(), color=(255,0,0))
                    for p in corners:
                        img.draw_circle(p[0], p[1], 5, color=(0,255,0))
                    valid_corners.append(corners)
            if len(valid_corners) >= 5:
                avg = average_corners(valid_corners[:5])
                avg = offset_corners(avg, k=0.03)

                # 画中心十字
                for x,y in avg:
                    img.draw_cross(x, y)

            # 将结果显示到屏幕
            Display.show_image(img)
            img = None

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
