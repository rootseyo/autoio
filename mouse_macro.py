import time
import threading
from pynput import mouse, keyboard

class MouseMacro:
    def __init__(self):
        self.recording = False
        self.playing = False
        self.events = []
        self.start_time = None
        self.mouse_controller = mouse.Controller()
        
    def on_press(self, key):
        try:
            if key == keyboard.Key.f8:
                if not self.playing:
                    self.toggle_recording()
            elif key == keyboard.Key.f9:
                if self.playing:
                    print("\n[STOP] 재생 중지 요청됨...")
                    self.playing = False  # Stop the loop in play_back
                elif not self.recording:
                    try:
                        # Note: input() blocks the listener thread on Windows if not handled carefully.
                        # However, in this threading model, it's manageable.
                        count_str = input("\n[INPUT] 반복 횟수를 입력하세요 (기본 1, 무한 -1): ").strip()
                        count = int(count_str) if count_str else 1
                    except ValueError:
                        print("[ERROR] 숫자를 입력해주세요. 기본값 1회로 진행합니다.")
                        count = 1
                    
                    threading.Thread(target=self.play_back, args=(count,), daemon=True).start()
        except AttributeError:
            pass

    def toggle_recording(self):
        self.recording = not self.recording
        if self.recording:
            self.events = []
            self.start_time = time.time()
            print("\n[REC] 기록 시작... (중지하려면 F8)")
        else:
            print(f"[STOP] 기록 중지. 총 {len(self.events)}개 이벤트 저장됨.")

    def on_move(self, x, y):
        if self.recording:
            elapsed = time.time() - self.start_time
            self.events.append(('move', elapsed, x, y))
            print(f"[REC-MOVE] {elapsed:.2f}s | 위치: ({x}, {y})")

    def on_click(self, x, y, button, pressed):
        if self.recording:
            elapsed = time.time() - self.start_time
            state = "클릭" if pressed else "해제"
            self.events.append(('click', elapsed, x, y, button, pressed))
            print(f"[REC-CLICK] {elapsed:.2f}s | {button} {state} | 위치: ({x}, {y})")

    def play_back(self, count=1):
        if not self.events:
            print("[WARN] 재생할 기록이 없습니다.")
            return
            
        self.playing = True
        loop_count = 0
        while self.playing:
            if count != -1 and loop_count >= count:
                break
                
            loop_count += 1
            print(f"\n[PLAY] 재생 시작 ({loop_count}/{count if count != -1 else '무한'})...")
            start_playback = time.time()
            
            for event in self.events:
                if not self.playing: # 중간에 F9를 누르면 즉시 중단
                    break
                    
                event_type = event[0]
                event_time = event[1]
                
                # 타이밍 동기화
                current_elapsed = time.time() - start_playback
                sleep_time = event_time - current_elapsed
                
                # 중단 체크를 위해 짧게 나누어 대기
                while sleep_time > 0:
                    if not self.playing:
                        break
                    step = min(sleep_time, 0.05)
                    time.sleep(step)
                    sleep_time -= step
                
                if not self.playing: break

                if event_type == 'move':
                    x, y = event[2], event[3]
                    self.mouse_controller.position = (x, y)
                    print(f"[PLAY-MOVE] 위치: ({x}, {y})")
                elif event_type == 'click':
                    x, y, button, pressed = event[2], event[3], event[4], event[5]
                    self.mouse_controller.position = (x, y)
                    state = "클릭" if pressed else "해제"
                    print(f"[PLAY-CLICK] {button} {state} | 위치: ({x}, {y})")
                    
                    if pressed:
                        self.mouse_controller.press(button)
                    else:
                        self.mouse_controller.release(button)
        
        if not self.playing:
            print("\n[STOP] 사용자에 의해 재생이 강제 중단되었습니다.")
        else:
            print("\n[DONE] 모든 재생이 완료되었습니다.")
        
        self.playing = False

    def run(self):
        print("========================================")
        print(" Python Mouse Macro (F8: Rec, F9: Play) ")
        print("========================================")
        print("Status: Listening...")
        
        # Use context managers for listeners
        with mouse.Listener(on_move=self.on_move, on_click=self.on_click) as m_listener:
            with keyboard.Listener(on_press=self.on_press) as k_listener:
                k_listener.join()

if __name__ == "__main__":
    macro = MouseMacro()
    macro.run()
