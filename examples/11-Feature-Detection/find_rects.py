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
    sensor.skip_frames(time = 2000)
    sensor.set_auto_gain(False)
    sensor.set_auto_whitebal(False,(0,0,0))

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

def euler_distance(x1,y1,x2,y2):
    return ((x1-x2)**2+(y1-y2)**2)**(1/2)

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

            for r in img.find_rects(threshold = 10000):
                img.draw_rectangle([v for v in r.rect()], color = (255, 0, 0))
                for p in r.corners(): 
                    img.draw_circle(p[0], p[1], 5, color = (0, 255, 0))
                print(r)

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
