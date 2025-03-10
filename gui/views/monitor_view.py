from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from qfluentwidgets import (TextEdit, PrimaryPushButton, PushButton,
                          FluentIcon, InfoBar, InfoBarPosition)
import threading
import asyncio
import traceback
from PDD.app import monitor_all_accounts
from utils.logger import get_logger, get_log_queue


class MonitorThread(QThread):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(self, stop_event):
        super().__init__()
        self.stop_event = stop_event
        
    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(monitor_all_accounts(self.stop_event))
        except Exception as e:
            self.error.emit(str(e))
            traceback.print_exc()
        finally:
            self.finished.emit()


class MonitorView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName('monitorView')
        self.logger = get_logger('monitor')
        self.log_queue = get_log_queue()
        self.monitoring = False
        self.stop_event = threading.Event()
        self.monitor_thread = None
        
        self.initUI()
        self.start_log_listener()
        
    def initUI(self):
        self.output_text = TextEdit(self)
        self.output_text.setReadOnly(True)
        self.output_text.setPlaceholderText("监控日志将在此显示...")
        
        # 创建按钮
        self.start_button = PrimaryPushButton('开始监控', self, icon=FluentIcon.PLAY)
        self.stop_button = PushButton('停止监控', self, icon=FluentIcon.PAUSE)
        self.clear_button = PushButton('清空输出', self, icon=FluentIcon.DELETE)
        
        self.stop_button.setEnabled(False)
        
        # 连接信号
        self.start_button.clicked.connect(self.start_monitoring)
        self.stop_button.clicked.connect(self.stop_monitoring)
        self.clear_button.clicked.connect(self.clear_output)
        
        # 布局
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addStretch()
        
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.output_text)
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
        
    def start_log_listener(self):
        # 创建定时器检查日志队列
        self.timer = self.startTimer(100)
        
    def timerEvent(self, event):
        while not self.log_queue.empty():
            message = self.log_queue.get()
            self.update_output(message)
            
    def start_monitoring(self):
        if not self.monitoring:
            self.logger.info("开始监控...")
            self.monitoring = True
            self.stop_event.clear()
            
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            
            self.monitor_thread = MonitorThread(self.stop_event)
            self.monitor_thread.finished.connect(self.on_monitoring_finished)
            self.monitor_thread.error.connect(self.on_monitoring_error)
            self.monitor_thread.start()
            
            InfoBar.success(
                title='监控已启动',
                content='系统开始监控消息',
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            
    def stop_monitoring(self):
        if self.monitoring:
            self.stop_event.set()
            self.logger.info("正在停止监控，请稍候...")
            
            InfoBar.warning(
                title='正在停止',
                content='正在安全停止监控...',
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            
    def on_monitoring_finished(self):
        self.monitoring = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.logger.info("监控已完全停止")
        
        InfoBar.success(
            title='监控已停止',
            content='监控已安全停止',
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )
        
    def on_monitoring_error(self, error_msg):
        InfoBar.error(
            title='监控错误',
            content=f'发生错误: {error_msg}',
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=5000,
            parent=self
        )
        
    def clear_output(self):
        self.output_text.clear()
        
    def update_output(self, message):
        self.output_text.append(message)
        # 滚动到底部
        scrollbar = self.output_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum()) 