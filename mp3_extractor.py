import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import yt_dlp

class YouTubeAudioExtractorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("유튜브 다중 MP3 추출기")
        self.root.geometry("550x500")
        self.root.resizable(False, False)

        icon_path = "app_icon.ico"
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)

        self.output_dir = ""

        self.create_widgets()
        
    def get_ffmpeg_path(self):
        if getattr(sys, 'frozen', False):
            # PyInstaller로 패키징되어 실행될 때 (임시 폴더 경로)
            base_path = sys._MEIPASS
        else:
            # 일반 파이썬 에디터(.py)로 실행할 때 (현재 폴더 경로)
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        return os.path.join(base_path, 'ffmpeg.exe')

    def create_widgets(self):
        lbl_desc = ttk.Label(self.root, text="🎵 유튜브 링크를 한 줄에 하나씩 붙여넣으세요.", font=("맑은 고딕", 10, "bold"))
        lbl_desc.pack(pady=15)

        self.text_urls = tk.Text(self.root, width=65, height=10, font=("맑은 고딕", 9))
        self.text_urls.pack(pady=5, padx=20)

        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(pady=10)

        self.btn_extract = ttk.Button(btn_frame, text="일괄 다운로드 및 추출", command=self.start_extraction)
        self.btn_extract.grid(row=0, column=0, padx=5)

        btn_clear = ttk.Button(btn_frame, text="입력창 비우기", command=self.clear_text)
        btn_clear.grid(row=0, column=1, padx=5)

        btn_open_folder = ttk.Button(btn_frame, text="결과 폴더 열기", command=self.open_output_folder)
        btn_open_folder.grid(row=0, column=2, padx=5)

        status_frame = ttk.Frame(self.root)
        status_frame.pack(pady=10, fill="x", padx=20)

        self.lbl_status = ttk.Label(status_frame, text="대기 중...", foreground="blue")
        self.lbl_status.pack(pady=5)

        self.progress_var = tk.DoubleVar()
        self.progressbar = ttk.Progressbar(status_frame, variable=self.progress_var, maximum=100, length=400, mode='determinate')
        self.progressbar.pack(pady=5)

        # --- 🌟 퍼센트와 파일 카운트를 나란히 배치하기 위한 프레임 ---
        info_frame = ttk.Frame(status_frame)
        info_frame.pack()

        # 파일 진행 카운트 라벨 (예: 1/3)
        self.lbl_file_count = ttk.Label(info_frame, text="", font=("맑은 고딕", 9, "bold"), foreground="blue")
        self.lbl_file_count.pack(side="left", padx=5)

        # 퍼센트 라벨
        self.lbl_percent = ttk.Label(info_frame, text="0.0%")
        self.lbl_percent.pack(side="left", padx=5)
        # -----------------------------------------------------------

    def clear_text(self):
        self.text_urls.delete("1.0", tk.END)
        self.lbl_status.config(text="입력창이 비워졌습니다.", foreground="blue")
        self.progress_var.set(0)
        self.lbl_percent.config(text="0.0%")
        self.lbl_file_count.config(text="") # 카운트 초기화

    # 기존의 open_output_folder 함수를 이렇게 바꿔주세요
    def open_output_folder(self):
        if not self.output_dir or not os.path.exists(self.output_dir):
            messagebox.showinfo("알림", "아직 폴더가 지정되지 않았거나 폴더가 없습니다.\n먼저 추출을 진행해 주세요.")
            return
        try:
            os.startfile(self.output_dir)
        except Exception as e:
            messagebox.showerror("오류", f"폴더를 열 수 없습니다.\n경로: {self.output_dir}")

    def start_extraction(self):
        raw_text = self.text_urls.get("1.0", tk.END)
        urls = [url.strip() for url in raw_text.split('\n') if url.strip()]

        if not urls:
            messagebox.showwarning("경고", "추출할 유튜브 링크를 입력해 주세요.")
            return

        selected_dir = filedialog.askdirectory(title="MP3 파일을 저장할 폴더를 선택하세요")
        
        if not selected_dir:
            self.lbl_status.config(text="작업이 취소되었습니다. 폴더를 선택해 주세요.", foreground="darkorange")
            return
            
        self.output_dir = selected_dir

        self.btn_extract.config(state=tk.DISABLED)
        self.lbl_status.config(text=f"총 {len(urls)}개의 링크를 처리 시작합니다...", foreground="red")
        
        # UI 초기화
        self.progress_var.set(0)
        self.lbl_percent.config(text="0.0%")
        self.lbl_file_count.config(text=f"(0/{len(urls)})")
        
        threading.Thread(target=self.process_youtube, args=(urls,), daemon=True).start()

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes', 0)
            if total:
                percent = (downloaded / total) * 100
                self.root.after(0, self.update_progress_ui, percent)
                
        elif d['status'] == 'finished':
            self.root.after(0, self.update_status_ui, "다운로드 완료! MP3 파일로 변환 중... ⏳")

    def update_progress_ui(self, percent_val):
        self.progress_var.set(percent_val)
        self.lbl_percent.config(text=f"{percent_val:.1f}%")

    def update_status_ui(self, msg):
        self.lbl_status.config(text=msg, foreground="darkorange")

    def update_file_count_ui(self, current, total):
        self.lbl_file_count.config(text=f"({current}/{total})")

    # --- 🌟 개별 링크 반복 및 카운팅 처리부 ---
    def process_youtube(self, urls):
        ffmpeg_location = self.get_ffmpeg_path() 

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(self.output_dir, '%(title)s.%(ext)s'),
            'ffmpeg_location': ffmpeg_location, # 🌟 핵심: yt-dlp에게 이 경로의 ffmpeg를 쓰라고 강제 지시
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'progress_hooks': [self.progress_hook],
            'quiet': True,
            'no_warnings': True,
        }

        success = True
        total_files = len(urls)

        # URL 리스트를 한 번에 넘기지 않고 하나씩 꺼내서 작업
        for index, url in enumerate(urls):
            current_file_num = index + 1
            
            # 카운트 UI 업데이트 (예: 1/3)
            self.root.after(0, self.update_file_count_ui, current_file_num, total_files)
            
            # 새 파일 시작할 때마다 퍼센트 및 상태 라벨 초기화
            self.root.after(0, self.update_progress_ui, 0.0)
            self.root.after(0, self.update_status_ui, f"[{current_file_num}/{total_files}] 영상 다운로드 중...")

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url]) # 단일 링크 다운로드
            except Exception as e:
                print(f"다운로드 오류: {e}")
                success = False

        self.root.after(0, lambda: self.finish_extraction(success))
    # ------------------------------------------

    def finish_extraction(self, success):
        self.btn_extract.config(state=tk.NORMAL)
        if success:
            self.lbl_status.config(text="모든 추출이 성공적으로 완료되었습니다! 🎉", foreground="green")
            self.progress_var.set(100)
            self.lbl_percent.config(text="100.0%")
            
            messagebox.showinfo("완료", "유튜브 오디오 일괄 추출이 완료되었습니다.\n저장된 폴더를 엽니다.")
            self.open_output_folder()
        else:
            self.lbl_status.config(text="일부 작업 중 오류가 발생했습니다.", foreground="red")
            messagebox.showerror("오류", "음원 추출 중 문제가 발생했습니다. 잘못된 링크나 연령 제한 영상인지 확인해 주세요.")

if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeAudioExtractorApp(root)
    root.mainloop()