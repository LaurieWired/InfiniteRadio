import pystray
from pystray import MenuItem as item
from PIL import Image
import subprocess
import os
import webbrowser
import sys
import threading
import psutil
import tkinter as tk
from tkinter import simpledialog, messagebox, scrolledtext
from collections import deque

APP_ICON = "icon.png"
APP_NAME = "Infinite Radio"

# --- Helper for Tkinter dialogs ---
def show_dialog(title, prompt, initial_value=""):
    """Helper to run a Tkinter dialog."""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    user_input = simpledialog.askstring(title, prompt, initialvalue=initial_value)
    root.destroy()
    return user_input

class ConsoleWindow:
    """A Tkinter-based console window to display process output."""
    def __init__(self, parent_app):
        self.parent_app = parent_app
        self.process_runner = parent_app.dj_runner
        self.root = None
        self.text_widget = None

    def show(self):
        if self.root is None or not tk.Toplevel.winfo_exists(self.root):
            self._create_window()
        self.root.deiconify()
        self.root.lift()

    def _create_window(self):
        self.root = tk.Toplevel()
        self.root.title(f"{self.parent_app.get_dj_type_name()} Console")
        self.root.geometry("800x600")

        self.text_widget = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, state='disabled', font=("Courier New", 9))
        self.text_widget.pack(expand=True, fill='both')

        self.root.protocol("WM_DELETE_WINDOW", self.hide)
        self._update_content()

    def hide(self):
        if self.root:
            self.root.withdraw()

    def _update_content(self):
        if self.root and self.text_widget and self.process_runner:
            new_output = self.process_runner.get_output()
            if new_output:
                self.text_widget.config(state='normal')
                self.text_widget.insert(tk.END, new_output)
                self.text_widget.config(state='disabled')
                self.text_widget.see(tk.END)

        if self.root and tk.Toplevel.winfo_exists(self.root):
            self.root.after(500, self._update_content) # Poll every 500ms

    def destroy(self):
        if self.root:
            self.root.destroy()
            self.root = None

class ProcessRunner:
    """A helper class to manage a single background subprocess and capture its output."""
    def __init__(self, script_name, args):
        self.script_name = script_name
        self.args = args
        self.process = None
        self.output_buffer = deque()

    def start(self):
        if self.is_running():
            return False

        script_path = os.path.join(os.path.dirname(__file__), self.script_name)
        if not os.path.exists(script_path):
            messagebox.showerror("Error", f"Script not found: {self.script_name}")
            return False

        command = [sys.executable, '-u', script_path] + self.args
        print(f"Starting process: {' '.join(command)}")

        self.output_buffer.clear()

        # Use CREATE_NEW_PROCESS_GROUP to allow it to be killed properly.
        # Pipes are used to capture output.
        self.process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1, # Line buffered
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )

        self.output_thread = threading.Thread(target=self._read_output, daemon=True)
        self.output_thread.start()
        return True

    def _read_output(self):
        """Read output from the subprocess in a separate thread."""
        if not self.process or not self.process.stdout:
            return
        try:
            for line in iter(self.process.stdout.readline, ''):
                self.output_buffer.append(line)
        except Exception as e:
            print(f"Error reading output: {e}")

    def get_output(self):
        """Get all new output from the buffer as a string."""
        if not self.output_buffer:
            return ""

        lines = []
        while self.output_buffer:
            lines.append(self.output_buffer.popleft())
        return "".join(lines)

    def stop(self):
        if not self.is_running():
            return False

        print(f"Stopping process PID: {self.process.pid}")
        try:
            self.process.send_signal(subprocess.CTRL_BREAK_EVENT)
            self.process.wait(timeout=5)
        except (subprocess.TimeoutExpired, OSError):
            parent = psutil.Process(self.process.pid)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()
        self.process = None
        return True

    def is_running(self):
        return self.process is not None and self.process.poll() is None

class InfiniteRadioApp:
    def __init__(self):
        self.image = Image.open(APP_ICON)
        self.icon = pystray.Icon(APP_NAME, self.image, APP_NAME, menu=self.build_menu())
        self.ip, self.port = None, None
        self.dj_type = "process"
        self.model_name = "internvl3-2b-instruct"
        self.monitor_index = 1
        self.interval = 10
        self.console_window = None

        self.cleanup_orphaned_processes()
        self.dj_runner = ProcessRunner('process_dj.py', [])

    def run(self):
        self.icon.run()

    def get_dj_type_name(self):
        return "Process DJ" if self.dj_type == "process" else "LLM DJ"

    def build_menu(self):
        is_configured = self.ip is not None and self.port is not None
        is_running = self.dj_runner.is_running()

        start_stop_title = f"Stop {self.get_dj_type_name()}" if is_running else f"Start {self.get_dj_type_name()}"

        return pystray.Menu(
            item(start_stop_title, self.toggle_dj_process, enabled=is_configured),
            item('Open Infinite Radio UI', self.open_ui, enabled=is_configured),
            item('Show Console', self.show_console, enabled=is_running),
            pystray.Menu.SEPARATOR,
            item('DJ Type', pystray.Menu(
                item('Process DJ', lambda: self.set_dj_type('process'), checked=self.dj_type == 'process'),
                item('LLM DJ', lambda: self.set_dj_type('llm'), checked=self.dj_type == 'llm')
            )),
            item('Settings', pystray.Menu(
                item('Configure Server...', self.configure_server),
                item('Configure Model...', self.configure_model),
                item('Configure Monitor...', self.configure_monitor, enabled=self.dj_type == "llm"),
                item('Configure Interval...', self.configure_interval)
            )),
            pystray.Menu.SEPARATOR,
            item('Quit', self.quit_app)
        )

    def update_menu(self):
        self.icon.menu = self.build_menu()
        self.icon.update_menu()

    def show_console(self):
        if self.console_window is None:
            self.console_window = ConsoleWindow(self)
        self.console_window.show()

    def toggle_dj_process(self):
        if self.dj_runner.is_running():
            self.dj_runner.stop()
            if self.console_window:
                self.console_window.destroy()
                self.console_window = None
        else:
            self._update_runner_config()
            self.dj_runner.start()
        self.update_menu()

    def _update_runner_config(self):
        if self.dj_type == "process":
            self.dj_runner.script_name = 'process_dj.py'
            self.dj_runner.args = [self.ip, str(self.port), '--interval', str(self.interval)]
        else:
            self.dj_runner.script_name = 'llm_dj.py'
            self.dj_runner.args = [self.ip, str(self.port), '--model', self.model_name, '--monitor', str(self.monitor_index), '--interval', str(self.interval)]

    def set_dj_type(self, dj_type):
        if self.dj_runner.is_running(): self.toggle_dj_process()
        self.dj_type = dj_type
        if dj_type == "process" and self.interval == 10: self.interval = 5
        elif dj_type == "llm" and self.interval == 5: self.interval = 10
        self.update_menu()

    def configure_server(self):
        response = show_dialog("Configure Server", "Enter IP:Port", f"{self.ip or '127.0.0.1'}:{self.port or '8080'}")
        if response:
            try:
                ip, port = response.rsplit(':', 1)
                self.ip, self.port = ip.strip(), int(port.strip())
                self.update_menu()
            except Exception:
                messagebox.showerror("Invalid Input", "Use format IP:PORT")

    def configure_model(self):
        response = show_dialog("Configure Model", "Enter LLM Model Name", self.model_name)
        if response: self.model_name = response.strip()

    def configure_monitor(self):
        response = show_dialog("Configure Monitor", "Enter Monitor Number (1 for primary)", str(self.monitor_index))
        if response: self.monitor_index = int(response.strip())

    def configure_interval(self):
        response = show_dialog("Configure Interval", "Enter interval in seconds", str(self.interval))
        if response: self.interval = int(response.strip())

    def open_ui(self):
        if self.ip and self.port: webbrowser.open(f"http://{self.ip}:{self.port}")

    def quit_app(self):
        if self.dj_runner.is_running(): self.dj_runner.stop()
        if self.console_window: self.console_window.destroy()
        self.icon.stop()

    def cleanup_orphaned_processes(self):
        # This function is unchanged
        try:
            current_pid = os.getpid()
            for proc in psutil.process_iter(['pid', 'cmdline']):
                if not proc.info['cmdline']: continue
                cmdline_str = ' '.join(proc.info['cmdline'])
                if ('llm_dj.py' in cmdline_str or 'process_dj.py' in cmdline_str) and proc.pid != current_pid:
                    psutil.Process(proc.pid).terminate()
        except Exception as e:
            print(f"Error during cleanup: {e}")

if __name__ == "__main__":
    # Create a dummy root window for Tkinter dialogs and hide it
    root = tk.Tk()
    root.withdraw()
    app = InfiniteRadioApp()
    app.run()
