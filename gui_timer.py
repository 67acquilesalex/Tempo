import threading
import time
import tkinter as tk
from tkinter import messagebox
import os
import subprocess
import signal
import psutil

class TimerApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.geometry("600x450")
        self.root.title("Timer")

        # Campo para entrada de tempo
        self.enter_time = tk.Entry(self.root, font=("Helvetica", 30), justify='center')
        self.enter_time.grid(row=0, column=0, columnspan=4, padx=10, pady=20)
        self.enter_time.insert(0, "HH:MM:SS")

        # Botões de controle
        self.start_button = tk.Button(self.root, font=("Helvetica", 20), text="Iniciar", command=self.start_thread, width=12)
        self.start_button.grid(row=1, column=0, padx=10, pady=10)

        self.pause_button = tk.Button(self.root, font=("Helvetica", 20), text="Pausar", command=self.pause, width=12, state='disabled')
        self.pause_button.grid(row=1, column=1, padx=10, pady=10)

        self.stop_button = tk.Button(self.root, font=("Helvetica", 20), text="Parar", command=self.stop, width=12, state='disabled')
        self.stop_button.grid(row=1, column=2, padx=10, pady=10)

        self.coffee_button = tk.Button(self.root, font=("Helvetica", 20), text="Coffee Break", command=lambda: self.set_preset_timer(0, 15, 0), width=12)
        self.coffee_button.grid(row=1, column=3, padx=10, pady=10)

        self.lunch_button = tk.Button(self.root, font=("Helvetica", 20), text="Lunch Break", command=lambda: self.set_preset_timer(2, 0, 0), width=12)
        self.lunch_button.grid(row=2, column=0, columnspan=4, padx=10, pady=10)

        # Rótulo de tempo
        self.time_label = tk.Label(self.root, font=("Helvetica", 30), text="Tempo: 00:00:00")
        self.time_label.grid(row=3, column=0, columnspan=4, padx=10, pady=20)

        # Variáveis de controle
        self.stop_loop = False
        self.paused = False
        self.seconds_remaining = None  # Inicializa como None
        self.timer_thread = None
        self.ahk_process = None  # Processo do AutoHotkey
        self.monitor_thread = None

        self.flag_file_path = r"C:\Users\Mii_Reis\Documents\GitHub\Tempo\mouse_moving.flag"  # Caminho do arquivo de sinalização

        self.flag_detected = threading.Event()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

    def set_preset_timer(self, hours, minutes, seconds):
        self.enter_time.delete(0, tk.END)
        self.enter_time.insert(0, f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        duration_ms = hours * 3600000 + minutes * 60000 + seconds * 1000
        print(f"Preset timer set to {hours}h:{minutes}m:{seconds}s ({duration_ms} ms)")
        self.start_thread(preset=True, duration_ms=duration_ms)

    def start_thread(self, preset=False, duration_ms=0):
        if not self.timer_thread or not self.timer_thread.is_alive():
            print("Starting timer thread...")
            self.start_button.config(state='disabled')
            self.coffee_button.config(state='disabled')
            self.lunch_button.config(state='disabled')
            self.stop_button.config(state='normal')
            self.pause_button.config(state='normal')

            if preset and duration_ms > 0:
                self.duration_ms = duration_ms  # Armazena a duração para uso posterior
                self.start_ahk(duration_ms)

                # Inicia a thread de monitoramento do arquivo de sinalização
                self.monitor_thread = threading.Thread(target=self.monitor_flag_file_polling)
                self.monitor_thread.daemon = True
                self.monitor_thread.start()

            self.timer_thread = threading.Thread(target=self.start_timer)
            self.timer_thread.daemon = True
            self.timer_thread.start()

    def start_ahk(self, duration_ms=7200000):
        ahk_script_path = r"C:\Users\Mii_Reis\Documents\GitHub\Tempo\temp.ahk"
        ahk_exe_path = r"C:\Program Files\AutoHotkey\AutoHotkey.exe"

        print("Starting AutoHotkey script...")
        if not os.path.exists(ahk_exe_path):
            messagebox.showerror("Erro", f"AutoHotkey não encontrado em {ahk_exe_path}.")
            print(f"Erro: AutoHotkey não encontrado em {ahk_exe_path}.")
            return

        if not os.path.exists(ahk_script_path):
            messagebox.showerror("Erro", f"Script AHK não encontrado em {ahk_script_path}.")
            print(f"Erro: Script AHK não encontrado em {ahk_script_path}.")
            return

        self.terminate_all_ahk_instances()  # Encerra todas as instâncias existentes

        try:
            self.update_ahk_script(duration_ms)
            self.ahk_process = subprocess.Popen(
                [ahk_exe_path, ahk_script_path, str(duration_ms)],
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
            print(f"AutoHotkey script iniciado com duração {duration_ms} ms.")
        except Exception as e:
            messagebox.showerror("Erro ao iniciar AHK", f"Não foi possível iniciar o script AHK: {e}")
            print(f"Erro ao iniciar AHK: {e}")

    def update_ahk_script(self, duration_ms):
        ahk_script_path = r"C:\Users\Mii_Reis\Documents\GitHub\Tempo\temp.ahk"
        if os.path.exists(ahk_script_path):
            with open(ahk_script_path, "r", encoding="utf-8") as file:
                script_content = file.read()

            # Substitui a linha que define Duration
            new_duration_line = f"Duration := {duration_ms}"
            import re
            script_content_new = re.sub(r"Duration\s*:=\s*\d+", new_duration_line, script_content)
            if script_content != script_content_new:
                with open(ahk_script_path, "w", encoding="utf-8") as file:
                    file.write(script_content_new)
                print(f"Script AHK atualizado com Duration = {duration_ms} ms.")
            else:
                print("Nenhuma atualização necessária no script AHK.")

    def terminate_all_ahk_instances(self):
        print("Verificando e terminando instâncias existentes do AutoHotkey...")
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'].lower() == 'autohotkey.exe':
                    # Verifica se o comando inclui o script temp.ahk
                    if proc.info['cmdline'] and any('temp.ahk' in arg for arg in proc.info['cmdline']):
                        proc.terminate()
                        try:
                            proc.wait(timeout=5)
                            print(f"Instância do AutoHotkey (PID {proc.pid}) terminada.")
                        except psutil.TimeoutExpired:
                            proc.kill()
                            print(f"Instância do AutoHotkey (PID {proc.pid}) forçada a terminar.")
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

    def terminate_ahk(self):
        if self.ahk_process and self.ahk_process.poll() is None:
            print("Terminando o processo AutoHotkey...")
            try:
                if os.name == 'nt':
                    self.ahk_process.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    self.ahk_process.terminate()
                self.ahk_process.wait(timeout=5)
                print("Processo AutoHotkey terminado com sucesso.")
            except Exception as e:
                print(f"Erro ao encerrar o processo AHK: {e}")
            finally:
                self.ahk_process = None

    def monitor_flag_file_polling(self):
        print("Iniciando monitoramento do arquivo de sinalização...")
        while not self.stop_loop:
            if os.path.exists(self.flag_file_path):
                print("Arquivo de sinalização detectado.")
                self.on_flag_created()
                # Espera até que o arquivo seja deletado
                while os.path.exists(self.flag_file_path) and not self.stop_loop:
                    time.sleep(0.5)
                print("Arquivo de sinalização deletado.")
                self.on_flag_deleted()
            else:
                time.sleep(0.5)

    def on_flag_created(self):
        if not self.flag_detected.is_set():
            # Inicia o cronômetro com a duração definida
            self.seconds_remaining = self.duration_ms // 1000  # Converte milissegundos para segundos
            self.safe_update_time_label(self.format_time(self.seconds_remaining))
            print(f"Flag detectada: Iniciando o cronômetro com {self.seconds_remaining} segundos.")
            self.flag_detected.set()

    def on_flag_deleted(self):
        if self.flag_detected.is_set():
            # Para o cronômetro
            self.stop_loop = True
            self.safe_update_time_label("Tempo Esgotado!")
            print("Flag deletada: Parando o cronômetro.")
            self.reset_buttons()
            self.flag_detected.clear()

    def start_timer(self):
        print("Thread do cronômetro iniciada, aguardando sinalização para começar...")
        # Espera até que flag_detected seja setada
        self.flag_detected.wait()
        print("Cronômetro iniciado.")
        while not self.stop_loop:
            if self.seconds_remaining > 0 and not self.paused:
                self.seconds_remaining -= 1
                self.safe_update_time_label(self.format_time(self.seconds_remaining))
                print(f"Tempo restante: {self.format_time(self.seconds_remaining)}")
                time.sleep(1)
            else:
                time.sleep(0.1)

            if self.seconds_remaining <= 0:
                self.safe_update_time_label("Tempo Esgotado!")
                print("Tempo esgotado: Parando o cronômetro e terminando o AHK.")
                self.terminate_ahk()
                self.reset_buttons()
                break

    def safe_update_time_label(self, text):
        self.root.after(0, lambda: self.update_time_label(text))

    def update_time_label(self, text):
        self.time_label.config(text=f"Tempo: {text}")

    def format_time(self, seconds):
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def pause(self):
        if self.paused:
            self.paused = False
            self.pause_button.config(text="Pausar")
            print("Cronômetro retomado.")
        else:
            self.paused = True
            self.pause_button.config(text="Retomar")
            print("Cronômetro pausado.")

    def stop(self):
        print("Parando o cronômetro manualmente...")
        self.stop_loop = True
        self.paused = False
        self.pause_button.config(text="Pausar")
        self.terminate_ahk()
        self.reset_buttons()

    def reset_buttons(self):
        print("Reiniciando os botões do GUI.")
        self.start_button.config(state='normal')
        self.coffee_button.config(state='normal')
        self.lunch_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.pause_button.config(state='disabled')

    def on_closing(self):
        print("Encerrando a aplicação...")
        self.stop_loop = True
        self.terminate_all_ahk_instances()
        self.root.destroy()

if __name__ == "__main__":
    TimerApp()
