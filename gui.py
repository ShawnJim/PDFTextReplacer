import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import sys
import threading
import logging
from pdf_replacer_pymupdf import PyMuPDFTextReplacer, verify_replacements

# --- GUI Logger ---
class TextHandler(logging.Handler):
    """自定义日志处理器，将日志记录重定向到Tkinter的Text小部件"""
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.configure(state='disabled')
            self.text_widget.yview(tk.END)
        self.text_widget.after(0, append)

# --- 主应用 ---
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF 文本替换工具")
        self.geometry("700x550")

        # --- 变量 ---
        self.input_pdf_path = tk.StringVar()
        self.output_pdf_path = tk.StringVar()
        self.method = tk.StringVar(value='precise')
        self.verify = tk.BooleanVar(value=True)

        # --- UI 布局 ---
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 文件选择
        file_frame = ttk.LabelFrame(main_frame, text="文件路径", padding="10")
        file_frame.pack(fill=tk.X, pady=5)
        self._create_file_widgets(file_frame)

        # 规则编辑
        rules_frame = ttk.LabelFrame(main_frame, text="替换规则 (格式: 原文|译文)", padding="10")
        rules_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self._create_rules_editor(rules_frame)

        # 选项
        options_frame = ttk.LabelFrame(main_frame, text="选项", padding="10")
        options_frame.pack(fill=tk.X, pady=5)
        self._create_options_widgets(options_frame)

        # 控制按钮
        run_button = ttk.Button(main_frame, text="开始处理", command=self.start_processing_thread)
        run_button.pack(pady=10, fill=tk.X)

        # 日志输出
        log_frame = ttk.LabelFrame(main_frame, text="日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self._create_log_widget(log_frame)


    def _create_file_widgets(self, parent):
        ttk.Label(parent, text="输入PDF:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(parent, textvariable=self.input_pdf_path, width=60).grid(row=0, column=1, sticky=tk.EW)
        ttk.Button(parent, text="浏览...", command=self.browse_input_pdf).grid(row=0, column=2, padx=5)

        ttk.Label(parent, text="输出PDF:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(parent, textvariable=self.output_pdf_path, width=60).grid(row=1, column=1, sticky=tk.EW)
        ttk.Button(parent, text="选择...", command=self.browse_output_pdf).grid(row=1, column=2, padx=5)

        parent.columnconfigure(1, weight=1)

    def _create_rules_editor(self, parent):
        self.rules_text = tk.Text(parent, wrap=tk.WORD, height=8)
        self.rules_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        rules_scrollbar = ttk.Scrollbar(parent, command=self.rules_text.yview)
        rules_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.rules_text['yscrollcommand'] = rules_scrollbar.set
        # 设置占位符
        self.rules_text.insert(tk.END, """# 在这里输入规则, 每行一条, 例如: 
# old text|new text
""")

    def _create_options_widgets(self, parent):
        ttk.Label(parent, text="替换方法:").pack(side=tk.LEFT, padx=5)
        methods = ['precise', 'overlay', 'hybrid']
        method_menu = ttk.OptionMenu(parent, self.method, self.method.get(), *methods)
        method_menu.pack(side=tk.LEFT, padx=5)

        verify_check = ttk.Checkbutton(parent, text="处理后验证结果", variable=self.verify)
        verify_check.pack(side=tk.RIGHT, padx=20)

    def _create_log_widget(self, parent):
        log_text = tk.Text(parent, state='disabled', wrap=tk.WORD, height=10)
        log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(parent, command=log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        log_text['yscrollcommand'] = scrollbar.set

        # 设置日志
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        # 移除所有现有的处理器
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        # 添加GUI处理器
        gui_handler = TextHandler(log_text)
        gui_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(gui_handler)



    def browse_input_pdf(self):
        path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if path:
            self.input_pdf_path.set(path)
            # 自动生成输出文件名
            if not self.output_pdf_path.get():
                base, ext = os.path.splitext(path)
                self.output_pdf_path.set(f"{base}_replaced{ext}")

    def browse_output_pdf(self):
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Files", "*.pdf")])
        if path:
            self.output_pdf_path.set(path)

    def get_resource_path(self, relative_path):
        """获取资源的绝对路径，用于处理打包后的情况"""
        try:
            # PyInstaller 创建一个临时文件夹并将路径存储在 _MEIPASS 中
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    def start_processing_thread(self):
        # 在新线程中运行，防止GUI冻结
        processing_thread = threading.Thread(target=self.process_pdf, daemon=True)
        processing_thread.start()

    def process_pdf(self):
        input_pdf = self.input_pdf_path.get()
        output_pdf = self.output_pdf_path.get()
        rules_text = self.rules_text.get("1.0", tk.END)

        # --- 输入验证 ---
        if not all([input_pdf, output_pdf, rules_text.strip()]):
            messagebox.showerror("错误", "输入/输出路径和规则内容都必须填写！")
            return
        if not os.path.exists(input_pdf):
            messagebox.showerror("错误", f"输入文件不存在: {input_pdf}")
            return
        if os.path.abspath(input_pdf) == os.path.abspath(output_pdf):
            messagebox.showerror("错误", "输出文件不能与输入文件相同！")
            return

        # 从文本框解析规则
        rules = {}
        for line_num, line in enumerate(rules_text.splitlines(), 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split('|')
            if len(parts) != 2:
                messagebox.showerror("规则错误", f"规则第 {line_num} 行格式错误: {line}")
                return
            rules[parts[0].strip()] = parts[1].strip()

        if not rules:
            messagebox.showerror("错误", "没有有效的规则可供使用！")
            return

        try:
            logging.info("="*30)
            logging.info("开始处理...")
            
            # 关键：直接将规则字典传递给替换器
            replacer = PyMuPDFTextReplacer(rules)
            replacer.fonts_dir = self.get_resource_path('fonts')
            logging.info(f"字体目录设置为: {replacer.fonts_dir}")

            replacer.replace_pdf(input_pdf, output_pdf, method=self.method.get())

            if self.verify.get():
                failed_rules = verify_replacements(output_pdf, replacer.rules)
                if failed_rules:
                    logging.warning(f"有 {len(failed_rules)} 条规则未成功替换。")
                else:
                    logging.info("所有规则均已成功验证！")
            
            logging.info("处理全部完成！")
            messagebox.showinfo("成功", f"处理完成！\n输出文件保存在: {output_pdf}")

        except Exception as e:
            logging.error(f"发生严重错误: {e}")
            import traceback
            logging.error(traceback.format_exc())
            messagebox.showerror("严重错误", f"处理失败，请查看日志获取详情。\n错误: {e}")

if __name__ == '__main__':
    app = App()
    app.mainloop()
