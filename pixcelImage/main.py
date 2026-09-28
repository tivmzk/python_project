import os
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image
from collections import Counter

def convert_fake_pixel_to_real(input_path, target_w, target_h):
    dir_name, file_name = os.path.split(input_path)
    name, ext = os.path.splitext(file_name)
    output_path = os.path.join(dir_name, f"{name}_pixel_{target_w}x{target_h}.png")

    img = Image.open(input_path).convert('RGBA')
    orig_w, orig_h = img.size

    cell_w = orig_w / target_w
    cell_h = orig_h / target_h

    new_img = Image.new('RGBA', (target_w, target_h), (0, 0, 0, 0))

    for y in range(target_h):
        for x in range(target_w):
            # 블록의 범위 계산 (약간 안쪽의 60% 영역만 집중 조사하여 테두리 오차 제거)
            left = int((x + 0.2) * cell_w)
            right = int((x + 0.8) * cell_w)
            top = int((y + 0.2) * cell_h)
            bottom = int((y + 0.8) * cell_h)

            colors = []
            for px in range(left, max(left + 1, right)):
                for py in range(top, max(top + 1, bottom)):
                    r, g, b, a = img.getpixel((px, py))
                    
                    # 알파(투명도) 보정: 애매한 반투명 테두리는 완전 투명(0)으로 처리
                    if a < 128:
                        a = 0
                    else:
                        a = 255
                    
                    colors.append((r, g, b, a))

            # 블록 내부에서 가장 흔하게 등장한 색상(Mode) 선택
            if colors:
                most_common_color = Counter(colors).most_common(1)[0][0]
                new_img.putpixel((x, y), most_common_color)

    new_img.save(output_path, "PNG")
    return output_path

class PixelConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("픽셀 아트 변환기 (투명 배경 지원)")
        self.root.geometry("480x230")
        self.root.resizable(False, False)

        self.selected_file_path = ""

        # 1. 파일 선택 영역
        file_frame = tk.Frame(root)
        file_frame.pack(pady=15, fill="x", padx=20)

        self.file_label = tk.Label(file_frame, text="선택된 파일 없음", anchor="w", fg="gray", relief="sunken", bg="white", height=2)
        self.file_label.pack(side="left", fill="x", expand=True, padx=(0, 5))

        btn_select = tk.Button(file_frame, text="파일 선택", command=self.select_file, width=10, height=2)
        btn_select.pack(side="right")

        # 2. 해상도 입력 영역
        size_frame = tk.Frame(root)
        size_frame.pack(pady=10)

        tk.Label(size_frame, text="목표 가로 크기(px):").grid(row=0, column=0, padx=5, pady=5)
        self.entry_width = tk.Entry(size_frame, width=8, justify="center")
        self.entry_width.insert(0, "32")
        self.entry_width.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(size_frame, text="목표 세로 크기(px):").grid(row=0, column=2, padx=5, pady=5)
        self.entry_height = tk.Entry(size_frame, width=8, justify="center")
        self.entry_height.insert(0, "32")
        self.entry_height.grid(row=0, column=3, padx=5, pady=5)

        # 3. 변환 실행 버튼
        btn_convert = tk.Button(root, text="진짜 픽셀 이미지로 변환", command=self.run_conversion, bg="#4CAF50", fg="white", font=("맑은 고딕", 11, "bold"), height=2)
        btn_convert.pack(pady=15, fill="x", padx=20)

    def select_file(self):
        file_path = filedialog.askopenfilename(
            title="변환할 픽셀 이미지 선택",
            filetypes=[("PNG 이미지 (투명 배경 권장)", "*.png"), ("모든 이미지 파일", "*.png *.jpg *.jpeg *.bmp *.webp")]
        )
        if file_path:
            self.selected_file_path = file_path
            self.file_label.config(text=file_path, fg="black")

    def run_conversion(self):
        if not self.selected_file_path:
            messagebox.showwarning("경고", "먼저 목표가 되는 이미지 파일을 선택해 주세요.")
            return

        try:
            target_w = int(self.entry_width.get())
            target_h = int(self.entry_height.get())

            if target_w <= 0 or target_h <= 0:
                raise ValueError

        except ValueError:
            messagebox.showerror("오류", "가로 및 세로 크기에는 1 이상의 정수를 입력해 주세요.")
            return

        try:
            output_path = convert_fake_pixel_to_real(self.selected_file_path, target_w, target_h)
            messagebox.showinfo("성공", f"변환 완료!\n\n저장 경로:\n{output_path}")
        except Exception as e:
            messagebox.showerror("변환 실패", f"이미지 변환 중 오류가 발생했습니다:\n{e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = PixelConverterApp(root)
    root.mainloop()