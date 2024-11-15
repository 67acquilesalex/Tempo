import threading
import time
import customtkinter as ctk
from tkinter import messagebox
import os
import subprocess
import signal
import psutil
import re

# Configure CustomTkinter appearance
ctk.set_appearance_mode("system")  # Modes: "system" (default), "light", "dark"
ctk.set_default_color_theme("blue")  # Themes: "blue", "dark-blue", "green"

class TimerApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.geometry("600x450")
        self.root.title("Timer")
        self.root.resizable(False, False)  # Prevent resizing for consistent layout

        # Time entry field with rounded corners
        self.enter_time = ctk.CTkEntry(
            self.root,
            placeholder_text="00:00:00",
            font=("Helvetica", 30),
            justify='center',
            width=300,
            height=50,
            corner_radius=15  # Rounded corners
        )
        self.enter_time.grid(row=0, column=0, columnspan=4, padx=10, pady=20)
        self.enter_time.insert(0, "00:00:00")

        # Control buttons with rounded corners
        self.start_button = ctk.CTkButton(
            self.root,
            text="Start",
            command=self.start_manual_timer,
            width=120,
            height=50,
            font=("Helvetica", 20),
            corner_radius=15  # Rounded corners
        )
        self.start_button.grid(row=1, column=0, padx=10, pady=10)

        self.pause_button = ctk.CTkButton(
            self.root,
            text="Pause",
            command=self.pause,
            width=120,
            height=50,
            state='disabled',
            font=("Helvetica", 20),
            corner_radius=15  # Rounded corners
        )
        self.pause_button.grid(row=1, column=1, padx=10, pady=10)

        self.stop_button = ctk.CTkButton(
            self.root,
            text="Stop",
            command=self.stop,
            width=120,
            height=50,
            state='disabled',
            font=("Helvetica", 20),
            corner_radius=15  # Rounded corners
        )
        self.stop_button.grid(row=1, column=2, padx=10, pady=10)

        self.coffee_button = ctk.CTkButton(
            self.root,
            text="Coffee Break",
            command=lambda: self.set_preset_timer(0, 0, 15),  # 15 seconds
            width=160,
            height=50,
            font=("Helvetica", 20),
            corner_radius=15  # Rounded corners
        )
        self.coffee_button.grid(row=1, column=3, padx=10, pady=10)

        self.lunch_button = ctk.CTkButton(
            self.root,
            text="Lunch Break",
            command=lambda: self.set_preset_timer(2, 0, 0),  # 2 hours
            width=250,
            height=50,
            font=("Helvetica", 20),
            corner_radius=15  # Rounded corners
        )
        self.lunch_button.grid(row=2, column=0, columnspan=4, padx=10, pady=10)

        # Time label without bg_color or with 'transparent'
        self.time_label = ctk.CTkLabel(
            self.root,
            text="Time: 00:00:00",
            font=("Helvetica", 30),
            corner_radius=15,  # Rounded corners are optional for labels
            text_color="black",  # Ensure text is visible
            width=400,
            height=60,
            bg_color='transparent'  # Set to 'transparent' instead of None
        )
        self.time_label.grid(row=3, column=0, columnspan=4, padx=10, pady=20)

        # Control variables
        self.stop_loop = False
        self.paused = False
        self.seconds_remaining = None  # Initialize as None
        self.timer_thread = None
        self.ahk_process = None  # AutoHotkey process
        self.monitor_thread = None

        self.flag_file_path = r"C:\Users\Mii_Reis\Documents\GitHub\Tempo\mouse_moving.flag"  # Flag file path

        self.flag_detected = threading.Event()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

    def start_manual_timer(self):
        """Function to start the timer with manually entered duration."""
        time_str = self.enter_time.get()
        try:
            hours, minutes, seconds = map(int, time_str.split(':'))
            duration_ms = hours * 3600000 + minutes * 60000 + seconds * 1000
            if duration_ms <= 0:
                messagebox.showerror("Error", "Please enter a valid time greater than 0.")
                return
            print(f"Manual timer set to {hours}h:{minutes}m:{seconds}s ({duration_ms} ms)")
            self.start_thread(duration_ms=duration_ms)
        except ValueError:
            messagebox.showerror("Error", "Invalid time format. Use HH:MM:SS.")
            print("Error: Invalid time format.")

    def set_preset_timer(self, hours, minutes, seconds):
        """Function to set a preset timer."""
        self.enter_time.delete(0, ctk.END)
        self.enter_time.insert(0, f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        duration_ms = hours * 3600000 + minutes * 60000 + seconds * 1000
        print(f"Preset timer set to {hours}h:{minutes}m:{seconds}s ({duration_ms} ms)")
        self.start_thread(duration_ms=duration_ms)

    def start_thread(self, duration_ms=0):
        """Starts the timer thread and AutoHotkey script with the specified duration."""
        if not self.timer_thread or not self.timer_thread.is_alive():
            print("Starting timer thread...")
            self.start_button.configure(state='disabled')
            self.coffee_button.configure(state='disabled')
            self.lunch_button.configure(state='disabled')
            self.stop_button.configure(state='normal')
            self.pause_button.configure(state='normal')

            if duration_ms > 0:
                self.duration_ms = duration_ms  # Store duration for later use
                self.start_ahk(duration_ms)

                # Start monitoring thread for the flag file
                self.monitor_thread = threading.Thread(target=self.monitor_flag_file_polling, daemon=True)
                self.monitor_thread.start()

            self.timer_thread = threading.Thread(target=self.start_timer, daemon=True)
            self.timer_thread.start()

    def start_ahk(self, duration_ms=7200000):
        """Starts the AutoHotkey script with the specified duration."""
        ahk_script_path = r"C:\Users\Mii_Reis\Documents\GitHub\Tempo\temp.ahk"
        ahk_exe_path = r"C:\Program Files\AutoHotkey\AutoHotkey.exe"

        print("Starting AutoHotkey script...")
        if not os.path.exists(ahk_exe_path):
            messagebox.showerror("Error", f"AutoHotkey not found at {ahk_exe_path}.")
            print(f"Error: AutoHotkey not found at {ahk_exe_path}.")
            return

        if not os.path.exists(ahk_script_path):
            messagebox.showerror("Error", f"AHK script not found at {ahk_script_path}.")
            print(f"Error: AHK script not found at {ahk_script_path}.")
            return

        self.terminate_all_ahk_instances()  # Terminate existing instances

        try:
            self.update_ahk_script(duration_ms)
            self.ahk_process = subprocess.Popen(
                [ahk_exe_path, ahk_script_path, str(duration_ms)],
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
            print(f"AutoHotkey script started with duration {duration_ms} ms.")
        except Exception as e:
            messagebox.showerror("Error Starting AHK", f"Could not start AHK script: {e}")
            print(f"Error starting AHK: {e}")

    def update_ahk_script(self, duration_ms):
        """Updates the AHK script with the specified duration."""
        ahk_script_path = r"C:\Users\Mii_Reis\Documents\GitHub\Tempo\temp.ahk"
        if os.path.exists(ahk_script_path):
            with open(ahk_script_path, "r", encoding="utf-8") as file:
                script_content = file.read()

            # Replace the line that defines Duration
            new_duration_line = f"Duration := {duration_ms}"
            script_content_new = re.sub(r"Duration\s*:=\s*\d+", new_duration_line, script_content)
            if script_content != script_content_new:
                with open(ahk_script_path, "w", encoding="utf-8") as file:
                    file.write(script_content_new)
                print(f"AHK script updated with Duration = {duration_ms} ms.")
            else:
                print("No update needed for AHK script.")

    def terminate_all_ahk_instances(self):
        """Terminates all existing AutoHotkey instances."""
        print("Checking and terminating existing AutoHotkey instances...")
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'].lower() == 'autohotkey.exe':
                    # Check if the command includes the temp.ahk script
                    if proc.info['cmdline'] and any('temp.ahk' in arg for arg in proc.info['cmdline']):
                        proc.terminate()
                        try:
                            proc.wait(timeout=5)
                            print(f"Terminated AutoHotkey instance (PID {proc.pid}).")
                        except psutil.TimeoutExpired:
                            proc.kill()
                            print(f"Force killed AutoHotkey instance (PID {proc.pid}).")
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

    def terminate_ahk(self):
        """Terminates the AutoHotkey process."""
        if self.ahk_process and self.ahk_process.poll() is None:
            print("Terminating AutoHotkey process...")
            try:
                if os.name == 'nt':
                    self.ahk_process.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    self.ahk_process.terminate()
                self.ahk_process.wait(timeout=5)
                print("AutoHotkey process terminated successfully.")
            except Exception as e:
                print(f"Error terminating AHK process: {e}")
            finally:
                self.ahk_process = None

    def monitor_flag_file_polling(self):
        """Monitors the existence of the flag file to synchronize the timer."""
        print("Starting flag file monitoring...")
        while not self.stop_loop:
            if os.path.exists(self.flag_file_path):
                print("Flag file detected.")
                self.on_flag_created()
                # Wait until the file is deleted
                while os.path.exists(self.flag_file_path) and not self.stop_loop:
                    time.sleep(0.5)
                print("Flag file deleted.")
                self.on_flag_deleted()
            else:
                time.sleep(0.5)

    def on_flag_created(self):
        """Action when the flag file is created."""
        if not self.flag_detected.is_set():
            # Start the timer with the defined duration
            self.seconds_remaining = self.duration_ms // 1000  # Convert milliseconds to seconds
            self.safe_update_time_label(self.format_time(self.seconds_remaining))
            print(f"Flag detected: Starting timer with {self.seconds_remaining} seconds.")
            self.flag_detected.set()

    def on_flag_deleted(self):
        """Action when the flag file is deleted."""
        if self.flag_detected.is_set():
            # Stop the timer
            self.stop_loop = True
            self.safe_update_time_label("Time Out!")
            print("Flag deleted: Stopping timer.")
            self.reset_buttons()
            self.flag_detected.clear()

    def start_timer(self):
        """Thread that manages the countdown timer."""
        print("Timer thread started, waiting for flag to begin...")
        # Wait until flag_detected is set
        self.flag_detected.wait()
        print("Timer started.")
        while not self.stop_loop:
            if self.seconds_remaining > 0 and not self.paused:
                self.seconds_remaining -= 1
                self.safe_update_time_label(self.format_time(self.seconds_remaining))
                print(f"Time remaining: {self.format_time(self.seconds_remaining)}")
                time.sleep(1)
            else:
                time.sleep(0.1)

            if self.seconds_remaining <= 0:
                self.safe_update_time_label("Time's Up!")
                print("Time's up: Stopping timer and terminating AHK.")
                self.terminate_ahk()
                self.reset_buttons()
                break

    def safe_update_time_label(self, text):
        """Safely updates the time label in the main thread."""
        self.root.after(0, lambda: self.update_time_label(text))

    def update_time_label(self, text):
        """Updates the text of the time label."""
        self.time_label.configure(text=f"Time: {text}")

    def format_time(self, seconds):
        """Formats seconds into HH:MM:SS."""
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def pause(self):
        """Pauses or resumes the timer."""
        if self.paused:
            self.paused = False
            self.pause_button.configure(text="Pause")
            print("Timer resumed.")
        else:
            self.paused = True
            self.pause_button.configure(text="Resume")
            print("Timer paused.")

    def stop(self):
        """Manually stops the timer."""
        print("Stopping timer manually...")
        self.stop_loop = True
        self.paused = False
        self.pause_button.configure(text="Pause")
        self.terminate_ahk()
        self.reset_buttons()

    def reset_buttons(self):
        """Re-enables GUI buttons after timer ends."""
        print("Resetting GUI buttons.")
        self.start_button.configure(state='normal')
        self.coffee_button.configure(state='normal')
        self.lunch_button.configure(state='normal')
        self.stop_button.configure(state='disabled')
        self.pause_button.configure(state='disabled')

    def on_closing(self):
        """Action when closing the application."""
        print("Closing application...")
        self.stop_loop = True
        self.terminate_all_ahk_instances()
        self.root.destroy()

if __name__ == "__main__":
    TimerApp()
