import time
import threading
import tkinter as tk
from tkinter import messagebox
from pynput import mouse, keyboard

class MouseMacroGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Python Mouse Macro")
        self.root.geometry("400x350")
        
        self.recording = False
        self.playing = False
        self.events = []
        self.start_time = None
        self.mouse_controller = mouse.Controller()
        
        # UI Elements
        self.setup_ui()
        
        # Listeners
        self.k_listener = keyboard.Listener(on_press=self.on_press)
        self.k_listener.start()
        self.m_listener = mouse.Listener(on_move=self.on_move, on_click=self.on_click)
        self.m_listener.start()

    def setup_ui(self):
        # Instructions
        tk.Label(self.root, text="[ 단축키 안내 ]", font=("Arial", 12, "bold")).pack(pady=10)
        tk.Label(self.root, text="F8: 기록 시작 / 중지").pack()
        tk.Label(self.root, text="F9: 재생 시작 / 중지").pack()
        
        # Loop Input
        input_frame = tk.Frame(self.root)
        input_frame.pack(pady=20)
        tk.Label(input_frame, text="반복 횟수: ").pack(side=tk.LEFT)
        self.loop_entry = tk.Entry(input_frame, width=10)
        self.loop_entry.insert(0, "1")
        self.loop_entry.pack(side=tk.LEFT)
        tk.Label(input_frame, text=" (-1은 무한)").pack(side=tk.LEFT)
        
        # Status
        self.status_label = tk.Label(self.root, text="상태: 대기 중", fg="blue", font=("Arial", 10, "bold"))
        self.status_label.pack(pady=5)
        
        # Log Display
        tk.Label(self.root, text="[ 로그 ]").pack()
        self.log_text = tk.Text(self.root, height=8, width=50)
        self.log_text.pack(padx=10, pady=5)

    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        print(message) # Also print to console for debugging

    def update_status(self, text, color="black"):
        self.status_label.config(text=f"상태: {text}", fg=color)

    def on_press(self, key):
        try:
            if key == keyboard.Key.f8:
                if not self.playing:
                    self.root.after(0, self.toggle_recording)
            elif key == keyboard.Key.f9:
                if self.playing:
                    self.playing = False
                    self.log("[STOP] 재생 중지 요청됨")
                elif not self.recording:
                    self.root.after(0, self.start_playback_thread)
        except AttributeError:
            pass

    def toggle_recording(self):
        self.recording = not self.recording
        if self.recording:
            self.events = []
            self.start_time = time.time()
            self.update_status("기록 중...", "red")
            self.log("[REC] 기록을 시작합니다.")
        else:
            self.update_status("대기 중", "blue")
            self.log(f"[STOP] 기록 종료 ({len(self.events)}개 이벤트)")

    def on_move(self, x, y):
        if self.recording:
            elapsed = time.time() - self.start_time
            self.events.append(('move', elapsed, x, y))
            # Moving log is too fast for UI text box, just update console or limit frequency
            # self.log(f"Move: ({x}, {y})") 

    def on_click(self, x, y, button, pressed):
        if self.recording:
            elapsed = time.time() - self.start_time
            state = "클릭" if pressed else "해제"
            self.events.append(('click', elapsed, x, y, button, pressed))
            self.log(f"[CLICK] {button} {state} ({x}, {y})")

    def start_playback_thread(self):
        try:
            val = self.loop_entry.get().strip()
            count = int(val) if val else 1
        except ValueError:
            messagebox.showerror("에러", "반복 횟수에 숫자를 입력해주세요.")
            return

        if not self.events:
            messagebox.showwarning("경고", "기록된 내용이 없습니다.")
            return

        threading.Thread(target=self.play_back, args=(count,), daemon=True).start()

    def play_back(self, count=1):
        self.playing = True
        self.update_status("재생 중...", "green")
        
        loop_count = 0
        while self.playing:
            if count != -1 and loop_count >= count:
                break
            
            loop_count += 1
            self.log(f"\n[PLAY] {loop_count}회차 시작")
            start_playback = time.time()
            
            for event in self.events:
                if not self.playing: break
                
                event_type, event_time = event[0], event[1]
                current_elapsed = time.time() - start_playback
                sleep_time = event_time - current_elapsed
                
                while sleep_time > 0:
                    if not self.playing: break
                    step = min(sleep_time, 0.05)
                    time.sleep(step)
                    sleep_time -= step
                
                if not self.playing: break

                if event_type == 'move':
                    self.mouse_controller.position = (event[2], event[3])
                elif event_type == 'click':
                    self.mouse_controller.position = (event[2], event[3])
                    if event[5]:
                        self.mouse_controller.press(event[4])
                    else:
                        self.mouse_controller.release(event[4])
                    self.log(f"[PLAY] {event[4]} {'클릭' if event[5] else '해제'}")

        self.update_status("대기 중", "blue")
        if not self.playing:
            self.log("[STOP] 재생이 중단되었습니다.")
        else:
            self.log("[DONE] 재생이 완료되었습니다.")
        self.playing = False

if __name__ == "__main__":
    root = tk.Tk()
    app = MouseMacroGUI(root)
    root.mainloop()
