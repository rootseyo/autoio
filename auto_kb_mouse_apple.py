import time
import threading
import customtkinter as ctk
from tkinter import messagebox
from pynput import mouse, keyboard

# Set appearance mode and color theme
ctk.set_appearance_mode("light")  # Apple look is often clean light mode
ctk.set_default_color_theme("blue")

class AutoKeyboardMouse(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Window Configuration ---
        self.title("Auto Keyboard & Mouse")
        self.geometry("500x700")
        self.configure(fg_color="#F5F5F7")  # Classic Apple light gray background

        # State
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
        # --- Header ---
        self.header_label = ctk.CTkLabel(self, text="Auto Keyboard & Mouse", font=ctk.CTkFont(family="SF Pro Display", size=24, weight="bold"))
        self.header_label.pack(pady=(30, 10))

        self.status_indicator = ctk.CTkLabel(self, text="● IDLE", text_color="#8E8E93", font=ctk.CTkFont(size=14, weight="bold"))
        self.status_label = ctk.CTkLabel(self, text="Ready to record your actions", text_color="#1D1D1F", font=ctk.CTkFont(size=13))
        self.status_indicator.pack()
        self.status_label.pack(pady=(0, 20))

        # --- Main Container ---
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=30)

        # --- Control Card ---
        self.control_card = ctk.CTkFrame(self.main_frame, fg_color="#FFFFFF", corner_radius=15)
        self.control_card.pack(fill="x", pady=10)
        
        btn_container = ctk.CTkFrame(self.control_card, fg_color="transparent")
        btn_container.pack(pady=20, padx=20)

        self.rec_btn = ctk.CTkButton(btn_container, text="Record", fg_color="#FF3B30", hover_color="#FF453A", 
                                     width=140, height=45, corner_radius=10, font=ctk.CTkFont(weight="bold"),
                                     command=self.toggle_recording)
        self.rec_btn.grid(row=0, column=0, padx=10)
        
        self.play_btn = ctk.CTkButton(btn_container, text="Play", fg_color="#007AFF", hover_color="#0A84FF", 
                                      width=140, height=45, corner_radius=10, font=ctk.CTkFont(weight="bold"),
                                      command=self.start_playback_thread)
        self.play_btn.grid(row=0, column=1, padx=10)

        # --- Settings Card ---
        self.settings_card = ctk.CTkFrame(self.main_frame, fg_color="#FFFFFF", corner_radius=15)
        self.settings_card.pack(fill="x", pady=10)
        
        # Hotkey Row
        hk_frame = ctk.CTkFrame(self.settings_card, fg_color="transparent")
        hk_frame.pack(fill="x", padx=20, pady=(15, 5))
        
        ctk.CTkLabel(hk_frame, text="Hotkeys", font=ctk.CTkFont(weight="bold")).pack(side="left")
        
        self.play_hk_btn = ctk.CTkButton(hk_frame, text=f"Play: {self.play_hotkey.upper()}", width=80, height=28, 
                                         fg_color="#E5E5EA", text_color="#1D1D1F", hover_color="#D1D1D6", corner_radius=8,
                                         command=lambda: self.start_hotkey_assignment("play"))
        self.play_hk_btn.pack(side="right", padx=2)
        
        self.rec_hk_btn = ctk.CTkButton(hk_frame, text=f"Rec: {self.rec_hotkey.upper()}", width=80, height=28, 
                                        fg_color="#E5E5EA", text_color="#1D1D1F", hover_color="#D1D1D6", corner_radius=8,
                                        command=lambda: self.start_hotkey_assignment("rec"))
        self.rec_hk_btn.pack(side="right", padx=2)

        # Repeat Row
        repeat_frame = ctk.CTkFrame(self.settings_card, fg_color="transparent")
        repeat_frame.pack(fill="x", padx=20, pady=(5, 15))
        
        ctk.CTkLabel(repeat_frame, text="Repeat Count", font=ctk.CTkFont(weight="bold")).pack(side="left")
        ctk.CTkLabel(repeat_frame, text="(-1 for infinite)", font=ctk.CTkFont(size=11), text_color="gray").pack(side="left", padx=5)
        
        self.loop_entry = ctk.CTkEntry(repeat_frame, width=60, height=28, border_width=1, corner_radius=8, justify="center")
        self.loop_entry.insert(0, "1")
        self.loop_entry.pack(side="right")

        # --- Log Card ---
        self.log_card = ctk.CTkFrame(self.main_frame, fg_color="#FFFFFF", corner_radius=15)
        self.log_card.pack(fill="both", expand=True, pady=(10, 20))
        
        ctk.CTkLabel(self.log_card, text="Activity Log", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(10, 5))
        
        self.log_text = ctk.CTkTextbox(self.log_card, fg_color="transparent", text_color="#1D1D1F", font=ctk.CTkFont(size=12))
        self.log_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def log(self, message):
        self.log_text.insert("end", f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_text.see("end")

    def update_status_ui(self, status, color_hex, message):
        self.status_indicator.configure(text=f"● {status}", text_color=color_hex)
        self.status_label.configure(text=message)

    # --- Hotkey Assignment ---
    def start_hotkey_assignment(self, target):
        if target == "rec":
            self.rec_hk_btn.configure(text="Press Key...", fg_color="#FFD60A")
        else:
            self.play_hk_btn.configure(text="Press Key...", fg_color="#FFD60A")
        
        self.assigning_target = target
        self.root_focus = self.focus_get()

    def finish_hotkey_assignment(self, key_name):
        if hasattr(self, 'assigning_target'):
            if self.assigning_target == "rec":
                self.rec_hotkey = key_name
                self.rec_hk_btn.configure(text=f"Rec: {key_name.upper()}", fg_color="#E5E5EA")
            else:
                self.play_hotkey = key_name
                self.play_hk_btn.configure(text=f"Play: {key_name.upper()}", fg_color="#E5E5EA")
            del self.assigning_target

    # --- Event Handlers ---
    def on_key_press(self, key):
        try:
            if hasattr(key, 'name'): k_name = key.name
            elif hasattr(key, 'char'): k_name = key.char
            else: k_name = str(key)
            
            k_name = k_name.lower()

            # Hotkey Assignment
            if hasattr(self, 'assigning_target'):
                self.after(0, lambda n=k_name: self.finish_hotkey_assignment(n))
                return

            # Hotkey Detection
            if k_name == self.rec_hotkey:
                if not self.playing: self.after(0, self.toggle_recording)
                return
            elif k_name == self.play_hotkey:
                if self.playing: self.playing = False
                elif not self.recording: self.after(0, self.start_playback_thread)
                return

            if self.recording:
                elapsed = time.time() - self.start_time
                self.events.append(('key_down', elapsed, key))
                self.log(f"Key Down: {k_name}")
        except Exception: pass

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
            self.log(f"Mouse: {button} {state}")

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
            self.update_status_ui("RECORDING", "#FF3B30", "Recording your keyboard and mouse...")
            self.rec_btn.configure(text="Stop")
            self.play_btn.configure(state="disabled")
            self.log("Started recording.")
        else:
            self.update_status_ui("IDLE", "#8E8E93", f"Captured {len(self.events)} events")
            self.rec_btn.configure(text="Record")
            self.play_btn.configure(state="normal")
            self.log("Stopped recording.")

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
        self.update_status_ui("PLAYING", "#34C759", "Playing back recorded actions...")
        self.play_btn.configure(text="Stop")
        self.rec_btn.configure(state="disabled")
        
        loop_count = 0
        while self.playing:
            if count != -1 and loop_count >= count:
                break
            
            loop_count += 1
            self.log(f"Starting loop {loop_count}")
            start_playback = time.time()
            
            for event in self.events:
                if not self.playing: break
                e_type, e_time = event[0], event[1]
                
                # Timing
                sleep_time = e_time - (time.time() - start_playback)
                while sleep_time > 0:
                    if not self.playing: break
                    step = min(sleep_time, 0.02)
                    time.sleep(step)
                    sleep_time -= step
                
                if not self.playing: break

                if e_type == 'm_move': self.mouse_controller.position = (event[2], event[3])
                elif e_type == 'm_click':
                    self.mouse_controller.position = (event[2], event[3])
                    if event[5]: self.mouse_controller.press(event[4])
                    else: self.mouse_controller.release(event[4])
                elif e_type == 'm_scroll': self.mouse_controller.scroll(event[4], event[5])
                elif e_type == 'key_down': self.keyboard_controller.press(event[2])
                elif e_type == 'key_up': self.keyboard_controller.release(event[2])

        self.update_status_ui("IDLE", "#8E8E93", "Playback finished")
        self.play_btn.configure(text="Play")
        self.rec_btn.configure(state="normal")
        self.playing = False

if __name__ == "__main__":
    app = AutoKeyboardMouse()
    app.mainloop()
