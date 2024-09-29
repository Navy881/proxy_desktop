import sys
import ctypes
from ctypes import wintypes
import subprocess
import threading
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QTextEdit, QMainWindow, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QMouseEvent


# Подключение библиотеки dwmapi для работы с атрибутами окна
dwmapi = ctypes.WinDLL("dwmapi")
DWMWA_USE_IMMERSIVE_DARK_MODE = 20


class ConsoleOutput:
    """Класс для перенаправления вывода в текстовый виджет QTextEdit."""
    def __init__(self, text_edit):
        self.text_edit = text_edit

    def write(self, message):
        self.text_edit.insertPlainText(message)
        self.text_edit.ensureCursorVisible()  # Автоматическая прокрутка

    def flush(self):
        pass  # Для совместимости с sys.stdout


class ProxyApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Proxy Switcher")
        self.setGeometry(200, 200, 800, 400)

        # Применение темного режима для окна через WinAPI
        self.set_dark_mode()

        # Переменные для перемещения окна
        self.old_position = QPoint()

        # Текущее состояние прокси
        self.proxy_enabled = False
        self.xray_process = None  # Для хранения процесса Xray

        # Основной виджет и компоновка
        central_widget = QWidget(self)
        central_widget.setObjectName("central_widget")
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Устанавливаем цвет для основного окна через стилизацию
        central_widget.setStyleSheet("background-color: #202942;")  # Серый цвет

        # Кнопка для включения/выключения прокси
        self.button = QPushButton("Включить прокси", self)
        self.button.setFixedSize(150, 30)
        self.button.setStyleSheet("color: white; background-color: #30384f;")
        self.button.clicked.connect(self.toggle_proxy)
        layout.addWidget(self.button)

        # Поле для вывода текста консоли (с чёрным фоном и зелёным текстом)
        self.console_output = QTextEdit(self)
        self.console_output.setReadOnly(True)
        self.console_output.setStyleSheet(" color: green; background-color: black; border: none;")
        layout.addWidget(self.console_output)

        # Перенаправление стандартного вывода в текстовый виджет
        sys.stdout = ConsoleOutput(self.console_output)
        sys.stderr = ConsoleOutput(self.console_output)

    def set_dark_mode(self):
        """Включение темного режима для окна через WinAPI"""
        hwnd = wintypes.HWND(self.winId().__int__())  # Преобразование в HWND
        enable_dark_mode = ctypes.c_int(1)  # Активируем темный режим
        
        # Применяем темный режим, используя DwmSetWindowAttribute
        dwmapi.DwmSetWindowAttribute(
            hwnd,
            ctypes.c_int(DWMWA_USE_IMMERSIVE_DARK_MODE),
            ctypes.byref(enable_dark_mode),
            ctypes.sizeof(enable_dark_mode)
        )

    # def mousePressEvent(self, event: QMouseEvent):
    #     """Обработчик нажатия кнопки мыши для перемещения окна."""
    #     if event.button() == Qt.LeftButton:
    #         self.old_position = event.globalPos()

    # def mouseMoveEvent(self, event: QMouseEvent):
    #     """Обработчик перемещения мыши для перемещения окна."""
    #     delta = QPoint(event.globalPos() - self.old_position)
    #     self.move(self.x() + delta.x(), self.y() + delta.y())
    #     self.old_position = event.globalPos()

    def toggle_proxy(self):
        if not self.proxy_enabled:
            self.enable_proxy()
        else:
            self.disable_proxy()

    def enable_proxy(self):
        self.proxy_enabled = True
        self.button.setText("Отключить прокси")

        # Выполнение команды для включения системного прокси
        try:
            subprocess.run(['reg', 'add', r'HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings', '/v', 'ProxyEnable', '/t', 'REG_DWORD', '/d', '1', '/f'], check=True)
            subprocess.run(['reg', 'add', r'HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings', '/v', 'ProxyServer', '/t', 'REG_SZ', '/d', '127.0.0.1:10801', '/f'], check=True)
            print("Прокси включен.")
        except subprocess.CalledProcessError as e:
            print(f"Ошибка при включении прокси: {e}")

        # Запуск Xray через PowerShell с помощью Popen
        try:
            self.xray_process = subprocess.Popen(
                ['xray.exe', 'run', '-c', 'config.json'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW  # Скрываем окно
            )
            print("Xray запущен.")
            # Запуск потока для чтения вывода Xray
            threading.Thread(target=self.read_xray_output, daemon=True).start()
        except Exception as e:
            print(f"Ошибка при запуске Xray: {e}")

    def disable_proxy(self):
        self.proxy_enabled = False
        self.button.setText("Включить прокси")

        # Выполнение команды для отключения системного прокси
        try:
            subprocess.run(['reg', 'add', r'HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings', '/v', 'ProxyEnable', '/t', 'REG_DWORD', '/d', '0', '/f'], check=True)
            print("Прокси отключен.")
        except subprocess.CalledProcessError as e:
            print(f"Ошибка при отключении прокси: {e}")

        # Завершение процесса Xray, если он запущен
        if self.xray_process:
            try:
                self.xray_process.terminate()  # Отправляет сигнал завершения
                self.xray_process.wait()  # Ожидание завершения процесса
                print("Xray процесс завершен.")
            except Exception as e:
                print(f"Ошибка при завершении Xray: {e}")
            finally:
                self.xray_process = None  # Очистка переменной процесса

    def read_xray_output(self):
        """Чтение вывода xray.exe и вывод в текстовое поле."""
        while True:
            output = self.xray_process.stdout.readline()
            if output == '' and self.xray_process.poll() is not None:
                break
            if output:
                print(output.strip())  # Выводим в текстовый виджет через перенаправленный stdout

    def closeEvent(self, event):
        """Обработчик закрытия приложения."""
        self.disable_proxy()  # Выключаем прокси при закрытии
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ProxyApp()
    window.show()
    sys.exit(app.exec_())