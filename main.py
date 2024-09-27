import tkinter as tk
from tkinter.scrolledtext import ScrolledText
import subprocess
import threading
import sys


class ConsoleOutput:
    """Класс для перенаправления вывода в текстовый виджет."""
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, message):
        # Добавляем текст в конец виджета
        self.text_widget.insert(tk.END, message)
        self.text_widget.see(tk.END)  # Автоматическая прокрутка

    def flush(self):
        pass  # Необходимо для совместимости с sys.stdout


class ProxyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Proxy Switcher")

        # Текущее состояние прокси
        self.proxy_enabled = False
        self.xray_process = None  # Для хранения процесса Xray

        # Кнопка для включения/выключения прокси
        self.button = tk.Button(root, text="Включить прокси", command=self.toggle_proxy, width=25, height=3)
        self.button.pack(pady=20)

        # Поле для вывода текста консоли (с чёрным фоном и зелёным текстом)
        self.console_output = ScrolledText(root, wrap=tk.WORD, width=100, height=20, bg="black", fg="green")
        self.console_output.pack(pady=10)

        # Перенаправление стандартного вывода в текстовый виджет
        sys.stdout = ConsoleOutput(self.console_output)
        sys.stderr = ConsoleOutput(self.console_output)

        # Обработчик закрытия окна
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def toggle_proxy(self):
        if not self.proxy_enabled:
            self.enable_proxy()
        else:
            self.disable_proxy()

    def enable_proxy(self):
        self.proxy_enabled = True
        self.button.config(text="Отключить прокси")

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
        self.button.config(text="Включить прокси")

        # Выполнение команды для отключения системного прокси
        try:
            subprocess.run(['reg', 'add', r'HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings', '/v', 'ProxyEnable', '/t', 'REG_DWORD', '/d', '0', '/f'], check=True)
            print("Прокси отключен.")
        except subprocess.CalledProcessError as e:
            print(f"Ошибка при отключении прокси: {e}")

        # Завершение процесса Xray, если он запущен
        if self.xray_process:
            try:
                # Завершаем процесс Xray
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

    def on_closing(self):
        """Обработчик закрытия приложения."""
        self.disable_proxy()  # Выключаем прокси при закрытии
        self.root.destroy()    # Закрываем окно


if __name__ == "__main__":
    root = tk.Tk()
    app = ProxyApp(root)
    root.mainloop()