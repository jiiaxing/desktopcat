import sys
import os
import threading 
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QDesktopWidget
from PyQt5.QtGui import QPixmap, QCursor, QPainter, QColor
from PyQt5.QtCore import Qt, QTimer, QPoint, pyqtSlot, QObject, pyqtSignal
from pynput import keyboard # 使用 pynput

# =================================================================
# 开发者参数接口
# =================================================================
# 默认图像大小
DEFAULT_IMAGE_SIZE = (80, 80) 

# =================================================================
# 辅助函数：处理 PyInstaller 打包后的资源路径
# =================================================================
def resource_path(relative_path):
    """ 获取资源的绝对路径，无论是运行在开发环境还是打包后的环境 """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# =================================================================
# 动画素材接口
# =================================================================
ASSET_PATHS = {
    "chase_right": [
        "assets/walkingright1.png", "assets/walkingright2.png", 
        "assets/walkingright3.png", "assets/walkingright4.png"
    ],
    "chase_left": [
        "assets/walkingleft1.png", "assets/walkingleft2.png", 
        "assets/walkingleft3.png", "assets/walkingleft4.png"
    ],
    "idle": [
        "assets/idle1.png", "assets/idle2.png",
        "assets/idle3.png", "assets/idle4.png"
    ]
}

# =================================================================
# 辅助类：全局热键监听器 (F8/F9 单键) 
# =================================================================

class HotkeyListener(QObject):
    """在一个独立的线程中监听全局热键，并发送信号给 PyQt 主线程"""
    
    hotkey_toggle_chasing = pyqtSignal() # F8 信号
    hotkey_quit_program = pyqtSignal()    # F9 信号

    def __init__(self):
        super().__init__()
        self.listener = None
        
        # 定义功能键
        self.F8_KEY = keyboard.Key.f8
        self.F9_KEY = keyboard.Key.f9

    def start_listening(self):
        """启动键盘监听器"""
        self.listener_thread = threading.Thread(target=self._run_listener)
        self.listener_thread.daemon = True
        self.listener_thread.start()

    def _run_listener(self):
        """pynput 监听器的回调函数"""
        def on_press(key):
            # 1. 检查 F8 键 (切换跟随)
            if key == self.F8_KEY:
                self.hotkey_toggle_chasing.emit()
            
            # 2. 检查 F9 键 (退出程序)
            elif key == self.F9_KEY:
                self.hotkey_quit_program.emit()
        
        # F8/F9 单键不需要 on_release
        with keyboard.Listener(on_press=on_press) as self.listener:
            self.listener.join()

    def stop_listening(self):
        """停止键盘监听器"""
        if self.listener:
            self.listener.stop()


class DesktopPet(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Desktop Cat")
        
        # --- 窗口属性设置 ---
        self.setWindowFlags(Qt.FramelessWindowHint | 
                            Qt.WindowStaysOnTopHint | 
                            Qt.Tool) 
        self.setAttribute(Qt.WA_TranslucentBackground) 
        
        # 获取屏幕尺寸
        desktop = QDesktopWidget().screenGeometry()
        self.screen_width = desktop.width()
        self.screen_height = desktop.height()
        
        # 初始位置
        initial_x = self.screen_width - DEFAULT_IMAGE_SIZE[0] - 50 
        initial_y = self.screen_height - DEFAULT_IMAGE_SIZE[1] - 50
        self.setGeometry(initial_x, initial_y, DEFAULT_IMAGE_SIZE[0], DEFAULT_IMAGE_SIZE[1])
        
        # --- 状态与动画变量 ---
        self.current_state = "idle"
        self.current_frame = 0
        self.is_chasing = True 
        
        # 目标停靠位置 (屏幕右下角)
        self.target_x = self.screen_width - DEFAULT_IMAGE_SIZE[0]
        self.target_y = self.screen_height - DEFAULT_IMAGE_SIZE[1]
        
        self.pet_label = QLabel(self)
        self.pet_label.setGeometry(0, 0, DEFAULT_IMAGE_SIZE[0], DEFAULT_IMAGE_SIZE[1])
        
        self.load_frame()

        # --- 定时器 ---
        self.chase_timer = QTimer(self)
        self.chase_timer.timeout.connect(self.update_position)
        self.chase_timer.start(30)
        
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_timer.start(150)
        
        # --- 设置全局热键监听  ---
        self.hotkey_listener = HotkeyListener()
        
        # 连接 F8 信号
        self.hotkey_listener.hotkey_toggle_chasing.connect(self.toggle_chasing)
        # 连接 F9 信号
        self.hotkey_listener.hotkey_quit_program.connect(QApplication.instance().quit)
        
        print("【热键提示】已设置 F8 键用于切换跟随/停止状态。")
        print("【热键提示】已设置 F9 键用于退出程序。")

        self.hotkey_listener.start_listening()
        
        # 确保程序退出时，监听器也停止
        QApplication.instance().aboutToQuit.connect(self.hotkey_listener.stop_listening)

    @pyqtSlot()
    def toggle_chasing(self):
        """F8 热键的回调函数：切换跟随状态"""
        self.is_chasing = not self.is_chasing
        status = "【跟随模式】已开启" if self.is_chasing else "【跟随模式】已关闭，正移动到右下角"
        print(status)
        
    def load_frame(self):
        """加载当前状态和帧数的图片"""
        try:
            relative_path = ASSET_PATHS[self.current_state][self.current_frame]
            full_path = resource_path(relative_path)
            pixmap = QPixmap(full_path)
            
            if pixmap.isNull():
                 raise FileNotFoundError(f"Image not found at: {full_path}")

            scaled_pixmap = pixmap.scaled(
                DEFAULT_IMAGE_SIZE[0], DEFAULT_IMAGE_SIZE[1], 
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.pet_label.setPixmap(scaled_pixmap)
        
        except (KeyError, IndexError, FileNotFoundError) as e:
            # 占位符：绘制一个红色圆圈
            print(f"Warning: Failed to load image. {e}")
            placeholder = QPixmap(DEFAULT_IMAGE_SIZE[0], DEFAULT_IMAGE_SIZE[1])
            placeholder.fill(Qt.transparent)
            painter = QPainter(placeholder)
            painter.setBrush(QColor(255, 0, 0, 180))
            painter.drawEllipse(10, 10, DEFAULT_IMAGE_SIZE[0] - 20, DEFAULT_IMAGE_SIZE[1] - 20)
            painter.end()
            self.pet_label.setPixmap(placeholder)


    def update_animation(self):
        """根据当前状态切换动画帧"""
        frames = ASSET_PATHS.get(self.current_state, ASSET_PATHS["idle"])
        self.current_frame = (self.current_frame + 1) % len(frames)
        self.load_frame()


    def update_position(self):
        """计算猫咪的新位置 (追逐或停靠)"""
        cat_pos = self.pos()
        chase_speed = 8
        new_x, new_y = cat_pos.x(), cat_pos.y()
        new_state = self.current_state

        if self.is_chasing:
            # --- 追逐逻辑 ---
            mouse_pos = QCursor.pos()
            stop_distance = 50 
            dx = mouse_pos.x() - cat_pos.x()
            dy = mouse_pos.y() - cat_pos.y()

            if abs(dx) < stop_distance and abs(dy) < stop_distance:
                new_state = "idle"
            else:
                if abs(dx) > chase_speed:
                    new_x = cat_pos.x() + (chase_speed if dx > 0 else -chase_speed)
                    new_state = "chase_right" if dx > 0 else "chase_left"
                if abs(dy) > chase_speed:
                    new_y = cat_pos.y() + (chase_speed if dy > 0 else -chase_speed)
        else:
            # --- 移动到角落的逻辑 ---
            target_x, target_y = self.target_x, self.target_y
            dx = target_x - cat_pos.x()
            dy = target_y - cat_pos.y()

            # 检查是否已经到达目标点
            if abs(dx) <= chase_speed and abs(dy) <= chase_speed:
                # 已经到达，停下并设为 idle
                new_x = target_x
                new_y = target_y
                new_state = "idle"
            else:
                # 还在路上，继续移动并设置奔跑动画
                if abs(dx) > chase_speed:
                    new_x = cat_pos.x() + (chase_speed if dx > 0 else -chase_speed)
                if abs(dy) > chase_speed:
                    new_y = cat_pos.y() + (chase_speed if dy > 0 else -chase_speed)
                
                # 设置奔跑动画
                if abs(dx) > abs(dy): 
                    new_state = "chase_right" if dx > 0 else "chase_left"
                else: 
                    new_state = "chase_right" if dx > 0 else "chase_left"

        # 应用移动和状态变化
        self.move(new_x, new_y)
        if new_state != self.current_state:
            self.current_state = new_state
            if new_state in ["chase_right", "chase_left", "idle"]:
                self.current_frame = 0


if __name__ == '__main__':
    if not os.path.exists("assets"):
        print("----------------------------------------------------------")
        print("【提示】请在当前目录下创建 'assets' 文件夹，并放入透明 PNG 图片！")
        print("----------------------------------------------------------")
        
    app = QApplication(sys.argv)
    pet = DesktopPet()
    pet.show()
    sys.exit(app.exec_())