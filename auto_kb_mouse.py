import time
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from pynput import mouse, keyboard

class AutoKeyboardMouse:
    def __init__(self, root):
        self.root = root
        self.root.title("Auto Keyboard & Mouse")
        self.root.geometry("450x550")
        
        self.recording = False
        self.playing = False
        self.events = []
        self.start_time = None
        
        self.mouse_controller = mouse.Controller()
        self.keyboard_controller = keyboard.Controller()
        
        # Default Hotkeys
        self.rec_hotkey = "f8"
        self.play_hotkey = "f9"
        
        self.setup_ui()
        
        # Listeners
        self.k_listener = keyboard.Listener(on_press=self.on_key_press, on_release=self.on_key_release)
        self.k_listener.start()
        self.m_listener = mouse.Listener(on_move=self.on_move, on_click=self.on_click, on_scroll=self.on_scroll)
        self.m_listener.start()

    def setup_ui(self):
        style = ttk.Style()
        style.configure("TButton", padding=5)
        
        # --- Header ---
        tk.Label(self.root, text="Auto Keyboard & Mouse", font=("Arial", 16, "bold")).pack(pady=10)
        
        # --- Hotkey Settings ---
        hk_frame = tk.LabelFrame(self.root, text="Hotkey Settings", padx=10, pady=10)
        hk_frame.pack(fill="x", padx=20, pady=5)
        
        tk.Label(hk_frame, text="Record/Stop:").grid(row=0, column=0, sticky="w")
        self.rec_hk_var = tk.StringVar(value=self.rec_hotkey.upper())
        self.rec_entry = tk.Entry(hk_frame, textvariable=self.rec_hk_var, width=10, justify='center')
        self.rec_entry.grid(row=0, column=1, padx=5)
        self.rec_entry.bind("<FocusIn>", lambda e: self.rec_entry.config(bg="yellow"))
        self.rec_entry.bind("<Key>", self.update_rec_hk)

        tk.Label(hk_frame, text="Play/Stop:").grid(row=1, column=0, sticky="w", pady=5)
        self.play_hk_var = tk.StringVar(value=self.play_hotkey.upper())
        self.play_entry = tk.Entry(hk_frame, textvariable=self.play_hk_var, width=10, justify='center')
        self.play_entry.grid(row=1, column=1, padx=5)
        self.play_entry.bind("<FocusIn>", lambda e: self.play_entry.config(bg="yellow"))
        self.play_entry.bind("<Key>", self.update_play_hk)
        
        # --- Controls ---
        ctrl_frame = tk.Frame(self.root)
        ctrl_frame.pack(pady=10)
        
        self.rec_btn = tk.Button(ctrl_frame, text="Start Recording", width=15, bg="#ffcccc", command=self.toggle_recording)
        self.rec_btn.grid(row=0, column=0, padx=5)
        
        self.play_btn = tk.Button(ctrl_frame, text="Start Playback", width=15, bg="#ccffcc", command=self.start_playback_thread)
        self.play_btn.grid(row=0, column=1, padx=5)

        # --- Loop Settings ---
        loop_frame = tk.Frame(self.root)
        loop_frame.pack(pady=5)
        tk.Label(loop_frame, text="Repeat Count:").pack(side=tk.LEFT)
        self.loop_entry = tk.Entry(loop_frame, width=8)
        self.loop_entry.insert(0, "1")
        self.loop_entry.pack(side=tk.LEFT, padx=5)
        tk.Label(loop_frame, text="(-1 for infinite)").pack(side=tk.LEFT)
        
        # --- Status ---
        self.status_label = tk.Label(self.root, text="Status: IDLE", fg="blue", font=("Arial", 11, "bold"))
        self.status_label.pack(pady=5)
        
        # --- Log ---
        tk.Label(self.root, text="Log:").pack(anchor="w", padx=20)
        self.log_text = tk.Text(self.root, height=12, width=55)
        self.log_text.pack(padx=20, pady=5)
        
        tk.Label(self.root, text="Click entry box to change hotkey", font=("Arial", 8), fg="gray").pack()

    def log(self, message):
        self.log_text.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_text.see(tk.END)

    def update_status(self, text, color="black"):
        self.status_label.config(text=f"Status: {text}", fg=color)

    # --- Hotkey Management ---
    def update_rec_hk(self, event):
        key_name = event.keysym.lower()
        self.rec_hotkey = key_name
        self.rec_hk_var.set(key_name.upper())
        self.rec_entry.config(bg="white")
        self.root.focus_set()
        return "break"

    def update_play_hk(self, event):
        key_name = event.keysym.lower()
        self.play_hotkey = key_name
        self.play_hk_var.set(key_name.upper())
        self.play_entry.config(bg="white")
        self.root.focus_set()
        return "break"

    # --- Event Handlers ---
    def on_key_press(self, key):
        try:
            if hasattr(key, 'name'): k_name = key.name
            elif hasattr(key, 'char'): k_name = key.char
            else: k_name = str(key)
            
            # Hotkey Detection
            if k_name.lower() == self.rec_hotkey:
                if not self.playing:
                    self.root.after(0, self.toggle_recording)
                return
            elif k_name.lower() == self.play_hotkey:
                if self.playing:
                    self.playing = False
                elif not self.recording:
                    self.root.after(0, self.start_playback_thread)
                return

            if self.recording:
                elapsed = time.time() - self.start_time
                self.events.append(('key_down', elapsed, key))
                self.log(f"Key Down: {k_name}")
        except Exception as e:
            pass

    def on_key_release(self, key):
        if self.recording:
            elapsed = time.time() - self.start_time
            self.events.append(('key_up', elapsed, key))

    def on_move(self, x, y):
        if self.recording:
            elapsed = time.time() - self.start_time
            self.events.append(('m_move', elapsed, x, y))

    def on_click(self, x, y, button, pressed):
        if self.recording:
            elapsed = time.time() - self.start_time
            self.events.append(('m_click', elapsed, x, y, button, pressed))
            state = "Pressed" if pressed else "Released"
            self.log(f"Mouse: {button} {state} at ({x}, {y})")

    def on_scroll(self, x, y, dx, dy):
        if self.recording:
            elapsed = time.time() - self.start_time
            self.events.append(('m_scroll', elapsed, x, y, dx, dy))

    # --- Logic ---
    def toggle_recording(self):
        self.recording = not self.recording
        if self.recording:
            self.events = []
            self.start_time = time.time()
            self.update_status("RECORDING", "red")
            self.rec_btn.config(text="Stop Recording", bg="#ff9999")
            self.play_btn.config(state=tk.DISABLED)
            self.log("Recording started...")
        else:
            self.update_status("IDLE", "blue")
            self.rec_btn.config(text="Start Recording", bg="#ffcccc")
            self.play_btn.config(state=tk.NORMAL)
            self.log(f"Recording stopped. ({len(self.events)} events captured)")

    def start_playback_thread(self):
        if self.playing:
            self.playing = False
            return

        try:
            val = self.loop_entry.get().strip()
            count = int(val) if val else 1
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number for Repeat Count.")
            return

        if not self.events:
            messagebox.showwarning("Warning", "No events recorded to play.")
            return

        threading.Thread(target=self.play_back, args=(count,), daemon=True).start()

    def play_back(self, count=1):
        self.playing = True
        self.update_status("PLAYING", "green")
        self.play_btn.config(text="Stop Playback", bg="#99ff99")
        self.rec_btn.config(state=tk.DISABLED)
        
        loop_count = 0
        while self.playing:
            if count != -1 and loop_count >= count:
                break
            
            loop_count += 1
            self.log(f"Loop {loop_count} started")
            start_playback = time.time()
            
            for event in self.events:
                if not self.playing: break
                
                e_type, e_time = event[0], event[1]
                
                # Precise sleep with interrupt check
                sleep_time = e_time - (time.time() - start_playback)
                while sleep_time > 0:
                    if not self.playing: break
                    step = min(sleep_time, 0.02)
                    time.sleep(step)
                    sleep_time -= step
                
                if not self.playing: break

                if e_type == 'm_move':
                    self.mouse_controller.position = (event[2], event[3])
                elif e_type == 'm_click':
                    self.mouse_controller.position = (event[2], event[3])
                    if event[5]: self.mouse_controller.press(event[4])
                    else: self.mouse_controller.release(event[4])
                elif e_type == 'm_scroll':
                    self.mouse_controller.scroll(event[4], event[5])
                elif e_type == 'key_down':
                    self.keyboard_controller.press(event[2])
                elif e_type == 'key_up':
                    self.keyboard_controller.release(event[2])

        self.update_status("IDLE", "blue")
        self.play_btn.config(text="Start Playback", bg="#ccffcc")
        self.rec_btn.config(state=tk.NORMAL)
        self.log("Playback ended.")
        self.playing = False

if __name__ == "__main__":
    root = tk.Tk()
    app = AutoKeyboardMouse(root)
    root.mainloop()
