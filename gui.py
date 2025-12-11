"""
EPUB转TXT批量转换工具 - GUI界面
"""
import os
import sys
import json
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
from epub_parser import EpubParser
from text_splitter import TextSplitter

# 抑制macOS的NSOpenPanel警告（不影响功能）
if sys.platform == 'darwin':
    import warnings
    import os
    # 设置环境变量来抑制警告
    os.environ['PYTHONWARNINGS'] = 'ignore::RuntimeWarning'
    warnings.filterwarnings('ignore', category=RuntimeWarning)


class EpubConverterGUI:
    """EPUB转TXT转换工具GUI"""
    
    CONFIG_FILE = 'epub_converter_config.json'
    
    def __init__(self, root):
        self.root = root
        self.root.title("EPUB转TXT批量转换工具")
        self.root.geometry("900x700")
        
        # 设置窗口图标（如果有的话）
        try:
            # macOS 可能需要特殊处理
            pass
        except:
            pass
        
        # 变量
        self.selected_files = []
        self.output_dir = tk.StringVar()
        self.remember_dir = tk.BooleanVar()
        self.is_processing = False
        self.is_paused = False
        self.should_stop = False
        self.conversion_thread = None
        self.decision_log_auto_scroll = True  # 决策日志自动滚动标志
        
        # 加载配置
        self.load_config()
        
        # 创建UI
        self.create_widgets()
        
        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def load_config(self):
        """加载配置文件"""
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.output_dir.set(config.get('output_dir', ''))
                    self.remember_dir.set(config.get('remember_dir', False))
            except Exception as e:
                print(f"加载配置失败: {e}")
    
    def save_config(self):
        """保存配置文件"""
        if self.remember_dir.get():
            try:
                config = {
                    'output_dir': self.output_dir.get(),
                    'remember_dir': True
                }
                with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"保存配置失败: {e}")
    
    def create_widgets(self):
        """创建UI组件"""
        # 主容器
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # 1. 文件选择区域
        file_frame = ttk.LabelFrame(main_frame, text="选择EPUB文件", padding="10")
        file_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)
        
        ttk.Button(file_frame, text="选择文件", command=self.select_files).grid(row=0, column=0, padx=(0, 10))
        
        self.file_listbox = tk.Listbox(file_frame, height=4, selectmode=tk.EXTENDED)
        self.file_listbox.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        scrollbar_files = ttk.Scrollbar(file_frame, orient=tk.VERTICAL, command=self.file_listbox.yview)
        scrollbar_files.grid(row=0, column=2, sticky=(tk.N, tk.S))
        self.file_listbox.config(yscrollcommand=scrollbar_files.set)
        
        ttk.Button(file_frame, text="清除", command=self.clear_files).grid(row=0, column=3)
        
        # 2. 输出目录选择区域
        output_frame = ttk.LabelFrame(main_frame, text="输出目录", padding="10")
        output_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        output_frame.columnconfigure(1, weight=1)
        
        ttk.Button(output_frame, text="选择目录", command=self.select_output_dir).grid(row=0, column=0, padx=(0, 10))
        
        self.output_entry = ttk.Entry(output_frame, textvariable=self.output_dir, state='readonly')
        self.output_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        self.remember_check = ttk.Checkbutton(
            output_frame, 
            text="记住此目录为默认目录", 
            variable=self.remember_dir,
            command=self.save_config
        )
        self.remember_check.grid(row=0, column=2)
        
        # 3. 日志显示区域（带切换功能）
        log_container = ttk.Frame(main_frame)
        log_container.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_container.columnconfigure(0, weight=1)
        log_container.rowconfigure(1, weight=1)
        
        # 切换按钮区域
        log_switch_frame = ttk.Frame(log_container)
        log_switch_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        self.log_mode = tk.StringVar(value='conversion')  # 'conversion' 或 'decision'
        
        ttk.Radiobutton(
            log_switch_frame, 
            text="转换日志", 
            variable=self.log_mode, 
            value='conversion',
            command=self.switch_log_view
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Radiobutton(
            log_switch_frame, 
            text="决策日志", 
            variable=self.log_mode, 
            value='decision',
            command=self.switch_log_view
        ).pack(side=tk.LEFT)
        
        # 日志框架
        log_frame = ttk.LabelFrame(log_container, text="转换日志", padding="10")
        log_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # 转换日志文本区域
        self.log_text = scrolledtext.ScrolledText(
            log_frame, 
            wrap=tk.WORD, 
            font=('Consolas', 10),
            bg='#e8e8e8',  # 更明显的灰色背景（比f0f0f0更深）
            fg='#212121',  # 深灰色文字
            relief=tk.SUNKEN,
            borderwidth=2,
            highlightthickness=0,  # 移除高亮边框
            insertbackground='#212121',  # 光标颜色
            selectbackground='#b3d9ff',  # 选中文本背景色
            selectforeground='#000000',  # 选中文本前景色
            highlightbackground='#e8e8e8',  # 高亮边框颜色
            highlightcolor='#e8e8e8'  # 焦点时高亮颜色
        )
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 决策日志文本区域（初始隐藏，与转换日志在同一位置）
        self.decision_log_text = scrolledtext.ScrolledText(
            log_frame, 
            wrap=tk.WORD, 
            font=('Consolas', 9),
            bg='#e8e8e8',
            fg='#212121',
            relief=tk.SUNKEN,
            borderwidth=2,
            highlightthickness=0,
            insertbackground='#212121',
            selectbackground='#b3d9ff',
            selectforeground='#000000',
            highlightbackground='#e8e8e8',
            highlightcolor='#e8e8e8'
        )
        # 决策日志初始不显示，但使用相同的grid位置
        self.decision_log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.decision_log_text.grid_remove()
        
        # 绑定滚动事件，检测用户是否手动滚动
        def on_decision_scroll(*args):
            # 检查是否滚动到底部
            self.decision_log_text.see(tk.END)
            # 如果用户手动滚动，暂时禁用自动滚动
            # 通过检查滚动位置来判断
            pass
        
        def on_decision_scroll_wheel(event):
            # 用户手动滚动时，禁用自动滚动
            self.decision_log_auto_scroll = False
            # 5秒后重新启用自动滚动（如果用户没有继续滚动）
            self.root.after(5000, lambda: setattr(self, 'decision_log_auto_scroll', True))
        
        self.decision_log_text.bind('<MouseWheel>', on_decision_scroll_wheel)
        self.decision_log_text.bind('<Button-4>', on_decision_scroll_wheel)  # Linux
        self.decision_log_text.bind('<Button-5>', on_decision_scroll_wheel)  # Linux
        
        # 强制设置背景色（macOS可能需要多次设置）
        # 使用after方法确保在窗口显示后设置
        def force_bg_color():
            try:
                for text_widget in [self.log_text, self.decision_log_text]:
                    text_widget.config(bg='#e8e8e8', highlightbackground='#e8e8e8', highlightcolor='#e8e8e8')
                    # 设置内部Text组件的背景（ScrolledText内部包含Text组件）
                    for widget in text_widget.winfo_children():
                        if isinstance(widget, tk.Text):
                            widget.config(bg='#e8e8e8', highlightbackground='#e8e8e8', highlightcolor='#e8e8e8')
            except Exception as e:
                print(f"设置背景色失败: {e}")
        
        # 延迟设置，确保窗口已创建（多次设置确保生效）
        self.root.after(100, force_bg_color)
        self.root.after(500, force_bg_color)
        self.root.after(1000, force_bg_color)
        
        # 配置文本标签样式（用于高亮百分比）
        # 确保所有颜色都是深色，在白色背景上可见
        for text_widget in [self.log_text, self.decision_log_text]:
            text_widget.tag_config('percentage', foreground='#d32f2f', font=('Consolas', 11, 'bold'))
            text_widget.tag_config('arrow', foreground='#1976d2', font=('Consolas', 10, 'bold'))
            text_widget.tag_config('success', foreground='#2e7d32', font=('Consolas', 10, 'bold'))  # 深绿色
            text_widget.tag_config('error', foreground='#c62828', font=('Consolas', 10, 'bold'))  # 深红色
            text_widget.tag_config('filename', foreground='#1565c0', font=('Consolas', 10))  # 深蓝色
            text_widget.tag_config('normal', foreground='#212121', font=('Consolas', 10))  # 深灰色，默认文本
            text_widget.tag_config('debug', foreground='#616161', font=('Consolas', 9))  # 决策日志用灰色
        
        # 为决策日志添加专门的标签样式
        self.decision_log_text.tag_config('debug_info', foreground='#616161', font=('Consolas', 9))  # 普通信息
        self.decision_log_text.tag_config('debug_warning', foreground='#f57c00', font=('Consolas', 9, 'bold'))  # 警告（橙色）
        self.decision_log_text.tag_config('debug_error', foreground='#c62828', font=('Consolas', 9, 'bold'))  # 错误（红色）
        self.decision_log_text.tag_config('debug_success', foreground='#2e7d32', font=('Consolas', 9, 'bold'))  # 成功（绿色）
        self.decision_log_text.tag_config('debug_merge', foreground='#1976d2', font=('Consolas', 9))  # 合并操作（蓝色）
        self.decision_log_text.tag_config('debug_file', foreground='#7b1fa2', font=('Consolas', 9))  # 文件名（紫色）
        
        # 4. 控制按钮区域
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=3, column=0, columnspan=2, pady=(10, 0))
        
        self.start_button = ttk.Button(control_frame, text="开始转换", command=self.start_conversion)
        self.start_button.grid(row=0, column=0, padx=(0, 10))
        
        self.pause_button = ttk.Button(control_frame, text="暂停", command=self.pause_conversion, state='disabled')
        self.pause_button.grid(row=0, column=1, padx=(0, 10))
        
        self.resume_button = ttk.Button(control_frame, text="继续", command=self.resume_conversion, state='disabled')
        self.resume_button.grid(row=0, column=2, padx=(0, 10))
        
        self.stop_button = ttk.Button(control_frame, text="终止", command=self.stop_conversion, state='disabled')
        self.stop_button.grid(row=0, column=3, padx=(0, 10))
        
        self.clear_log_button = ttk.Button(control_frame, text="清除日志", command=self.clear_log)
        self.clear_log_button.grid(row=0, column=4)
        
        # 进度条
        self.progress = ttk.Progressbar(control_frame, mode='indeterminate')
        self.progress.grid(row=0, column=5, padx=(20, 0), sticky=(tk.W, tk.E))
        control_frame.columnconfigure(5, weight=1)
    
    def select_files(self):
        """选择EPUB文件"""
        files = filedialog.askopenfilenames(
            title="选择EPUB文件",
            filetypes=[("EPUB文件", "*.epub"), ("所有文件", "*.*")]
        )
        if files:
            self.selected_files.extend(files)
            self.update_file_listbox()
    
    def clear_files(self):
        """清除文件列表"""
        self.selected_files = []
        self.update_file_listbox()
    
    def update_file_listbox(self):
        """更新文件列表显示"""
        self.file_listbox.delete(0, tk.END)
        for file_path in self.selected_files:
            self.file_listbox.insert(tk.END, os.path.basename(file_path))
    
    def select_output_dir(self):
        """选择输出目录"""
        dir_path = filedialog.askdirectory(title="选择输出目录", initialdir=self.output_dir.get() or os.getcwd())
        if dir_path:
            self.output_dir.set(dir_path)
            if self.remember_dir.get():
                self.save_config()
    
    def switch_log_view(self):
        """切换日志视图"""
        mode = self.log_mode.get()
        if mode == 'conversion':
            # 显示转换日志
            self.decision_log_text.grid_remove()
            self.log_text.grid()
            log_frame = self.log_text.master
            log_frame.config(text="转换日志")
        else:
            # 显示决策日志
            self.log_text.grid_remove()
            self.decision_log_text.grid()
            log_frame = self.decision_log_text.master
            log_frame.config(text="决策日志")
    
    def clear_log(self):
        """清除日志"""
        mode = self.log_mode.get()
        if mode == 'conversion':
            self.log_text.delete(1.0, tk.END)
        else:
            self.decision_log_text.delete(1.0, tk.END)
    
    def log_decision(self, message, tag='debug_info'):
        """添加决策日志消息"""
        # 确保背景色设置正确
        try:
            current_bg = self.decision_log_text.cget('bg')
            white_colors = ['white', '#ffffff', '#FFFFFF', 'SystemWindowBackgroundColor', 
                          'systemWindowBackgroundColor', '#fafafa', '']
            if current_bg in white_colors:
                self.decision_log_text.config(bg='#e8e8e8', highlightbackground='#e8e8e8', highlightcolor='#e8e8e8')
                for widget in self.decision_log_text.winfo_children():
                    if isinstance(widget, tk.Text):
                        widget.config(bg='#e8e8e8', highlightbackground='#e8e8e8', highlightcolor='#e8e8e8')
        except:
            pass
        
        # 根据消息内容自动选择标签
        if tag == 'debug_info':
            if '警告' in message or '⚠' in message:
                tag = 'debug_warning'
            elif '错误' in message or '✗' in message or '失败' in message:
                tag = 'debug_error'
            elif '✓' in message or '成功' in message or '完成' in message:
                tag = 'debug_success'
            elif '合并' in message or '→' in message:
                tag = 'debug_merge'
            elif any(keyword in message for keyword in ['.txt', '_part', '文件:']):
                tag = 'debug_file'
        
        self.decision_log_text.insert(tk.END, message, tag)
        
        # 只在自动滚动启用时才滚动到底部
        if self.decision_log_auto_scroll:
            self.decision_log_text.see(tk.END)
        
        self.root.update_idletasks()
    
    def log_message(self, message, tags=None):
        """添加日志消息"""
        # 如果没有指定标签，使用默认的normal标签（深色）
        if tags is None:
            tags = ['normal']
        # 确保背景色设置正确（每次插入时强制检查）
        try:
            current_bg = self.log_text.cget('bg')
            # 检查是否是白色或系统默认色
            white_colors = ['white', '#ffffff', '#FFFFFF', 'SystemWindowBackgroundColor', 
                          'systemWindowBackgroundColor', '#fafafa', '']
            if current_bg in white_colors:
                # 强制设置为浅灰色
                self.log_text.config(bg='#e8e8e8', highlightbackground='#e8e8e8', highlightcolor='#e8e8e8')
                # 设置内部Text组件的背景（ScrolledText内部包含Text组件）
                for widget in self.log_text.winfo_children():
                    if isinstance(widget, tk.Text):
                        widget.config(bg='#e8e8e8', highlightbackground='#e8e8e8', highlightcolor='#e8e8e8')
        except:
            pass
        self.log_text.insert(tk.END, message, tags)
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def log_conversion_result(self, epub_file, output_files, total_words):
        """记录转换结果"""
        epub_name = os.path.basename(epub_file)
        
        # 计算每个输出文件的字数
        splitter = TextSplitter()
        results = []
        total_output_words = 0
        
        for output_file in output_files:
            words = splitter.count_words_in_file(output_file)
            total_output_words += words
            results.append((output_file, words))
        
        # 计算百分比
        if total_words > 0:
            percentage = (total_output_words / total_words) * 100
        else:
            percentage = 0
        
        # 显示结果
        self.log_message(f"\n", [])
        self.log_message(f"📖 ", [])
        self.log_message(f"{epub_name}\n", ['filename'])
        
        if len(results) == 1:
            # 单个文件，简单显示
            output_file, words = results[0]
            output_name = os.path.basename(output_file)
            file_percentage = (words / total_words * 100) if total_words > 0 else 0
            
            self.log_message(f"  ", [])
            self.log_message(f"{epub_name}", ['filename'])
            self.log_message(f" ", [])
            self.log_message(f" ──→ ", ['arrow'])
            self.log_message(f" ", [])
            self.log_message(f"{output_name}", ['filename'])
            self.log_message(f" (", [])
            self.log_message(f"{words:,}", [])
            self.log_message(f" 字, ", [])
            self.log_message(f"{file_percentage:.1f}%", ['percentage'])
            self.log_message(f")\n", [])
        else:
            # 多个文件，显示每个文件
            for i, (output_file, words) in enumerate(results, 1):
                output_name = os.path.basename(output_file)
                file_percentage = (words / total_words * 100) if total_words > 0 else 0
                
                self.log_message(f"  ", [])
                self.log_message(f"{epub_name}", ['filename'])
                self.log_message(f" ", [])
                self.log_message(f" ──→ ", ['arrow'])
                self.log_message(f" ", [])
                self.log_message(f"{output_name}", ['filename'])
                self.log_message(f" (", [])
                self.log_message(f"{words:,}", [])
                self.log_message(f" 字, ", [])
                self.log_message(f"{file_percentage:.1f}%", ['percentage'])
                self.log_message(f")\n", [])
        
        # 总计信息
        self.log_message(f"  ", [])
        self.log_message(f"总计: ", [])
        self.log_message(f"{total_output_words:,}", [])
        self.log_message(f" 字 / ", [])
        self.log_message(f"{total_words:,}", [])
        self.log_message(f" 字 = ", [])
        self.log_message(f"{percentage:.1f}%", ['percentage'])
        self.log_message(f"\n", [])
        self.log_message(f"{'─' * 80}\n", [])
    
    def start_conversion(self):
        """开始转换"""
        if self.is_processing:
            messagebox.showwarning("警告", "转换正在进行中，请稍候...")
            return
        
        if not self.selected_files:
            messagebox.showwarning("警告", "请先选择要转换的EPUB文件！")
            return
        
        output_dir = self.output_dir.get().strip()
        if not output_dir:
            messagebox.showwarning("警告", "请先选择输出目录！")
            return
        
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception as e:
                messagebox.showerror("错误", f"无法创建输出目录: {e}")
                return
        
        # 保存配置
        if self.remember_dir.get():
            self.save_config()
        
        # 在新线程中执行转换
        self.is_processing = True
        self.is_paused = False
        self.should_stop = False
        self.start_button.config(state='disabled')
        self.pause_button.config(state='normal')
        self.resume_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.progress.start()
        
        self.conversion_thread = threading.Thread(target=self.convert_files, args=(output_dir,))
        self.conversion_thread.daemon = True
        self.conversion_thread.start()
    
    def pause_conversion(self):
        """暂停转换"""
        if self.is_processing and not self.is_paused:
            self.is_paused = True
            self.pause_button.config(state='disabled')
            self.resume_button.config(state='normal')
            self.log_message("⏸ 转换已暂停\n", ['success'])
    
    def resume_conversion(self):
        """继续转换"""
        if self.is_processing and self.is_paused:
            self.is_paused = False
            self.pause_button.config(state='normal')
            self.resume_button.config(state='disabled')
            self.log_message("▶ 转换已继续\n", ['success'])
    
    def stop_conversion(self):
        """终止转换"""
        if self.is_processing:
            if messagebox.askyesno("确认", "确定要终止当前转换吗？"):
                self.should_stop = True
                self.is_paused = False
                self.log_message("⏹ 正在终止转换...\n", ['error'])
    
    def convert_files(self, output_dir):
        """转换文件（在后台线程中执行）"""
        parser = EpubParser()
        splitter = TextSplitter()
        
        total_files = len(self.selected_files)
        success_count = 0
        fail_count = 0
        
        self.log_message(f"开始处理 {total_files} 个文件...\n", ['success'])
        self.log_message(f"{'=' * 80}\n", [])
        
        for idx, epub_file in enumerate(self.selected_files, 1):
            # 检查是否需要停止
            if self.should_stop:
                self.log_message(f"\n转换已终止（已处理 {idx-1}/{total_files} 个文件）\n", ['error'])
                break
            
            # 等待暂停状态解除
            while self.is_paused and not self.should_stop:
                threading.Event().wait(0.1)
            
            if self.should_stop:
                break
            
            try:
                self.log_message(f"[{idx}/{total_files}] 处理: {os.path.basename(epub_file)}\n", [])
                
                # 提取章节信息
                chapters = parser.extract_chapters(epub_file)
                
                if not chapters:
                    self.log_message(f"  ✗ 无法提取章节信息\n", ['error'])
                    fail_count += 1
                    continue
                
                # 统计总字数（只统计章节内容，不包括标题）
                total_words = sum(splitter.count_content_words(ch['content']) for ch in chapters)
                
                # 计算分割份数
                split_count = splitter.calculate_split_count(total_words)
                
                base_name = os.path.splitext(os.path.basename(epub_file))[0]
                output_files = []
                
                if split_count > 1:
                    # 需要分割（使用新规则：按8万字在章节边界切分）
                    chapter_groups = splitter.split_by_word_count_at_chapter_boundary(chapters)
                    
                    for i, group in enumerate(chapter_groups):
                        output_filename = f"{base_name}_part{i+1:02d}.txt"
                        output_path = os.path.join(output_dir, output_filename)
                        splitter.write_chapters_to_file(group, output_path)
                        output_files.append(output_path)
                    
                    # 合并字数过小的相邻文件（启用调试日志，输出到GUI）
                    def decision_log_callback(msg):
                        # 检查是否需要停止
                        if self.should_stop:
                            return
                        # 等待暂停状态解除
                        while self.is_paused and not self.should_stop:
                            threading.Event().wait(0.1)
                        if not self.should_stop:
                            self.root.after(0, lambda m=msg: self.log_decision(m))
                    output_files = splitter.merge_small_files(output_files, debug=True, log_callback=decision_log_callback)
                    
                    # 检查是否需要停止
                    if self.should_stop:
                        break
                else:
                    # 不需要分割
                    output_filename = f"{base_name}.txt"
                    output_path = os.path.join(output_dir, output_filename)
                    parser.convert_to_txt(epub_file, output_path)
                    output_files.append(output_path)
                
                # 检查是否需要停止
                if self.should_stop:
                    break
                
                # 记录转换结果
                self.log_conversion_result(epub_file, output_files, total_words)
                success_count += 1
                
            except Exception as e:
                self.log_message(f"  ✗ 处理失败: {e}\n", ['error'])
                fail_count += 1
        
        # 完成
        self.log_message(f"\n", [])
        self.log_message(f"{'=' * 80}\n", [])
        if self.should_stop:
            self.log_message(f"转换已终止！成功: {success_count} 个，失败: {fail_count} 个\n", ['error'])
        else:
            self.log_message(f"处理完成！成功: {success_count} 个，失败: {fail_count} 个\n", ['success'])
        
        # 恢复UI状态
        self.root.after(0, self.conversion_complete)
    
    def conversion_complete(self):
        """转换完成"""
        self.is_processing = False
        self.is_paused = False
        self.should_stop = False
        self.start_button.config(state='normal')
        self.pause_button.config(state='disabled')
        self.resume_button.config(state='disabled')
        self.stop_button.config(state='disabled')
        self.progress.stop()
        if not self.should_stop:
            messagebox.showinfo("完成", "转换完成！")


    def on_closing(self):
        """窗口关闭事件"""
        if self.is_processing:
            if not messagebox.askokcancel("退出", "转换正在进行中，确定要退出吗？"):
                return
        
        # 保存配置
        if self.remember_dir.get():
            self.save_config()
        
        self.root.destroy()


def main():
    """主函数"""
    # 抑制macOS的NSOpenPanel警告（在创建Tk之前设置）
    if sys.platform == 'darwin':
        import warnings
        warnings.filterwarnings('ignore')
    
    root = tk.Tk()
    app = EpubConverterGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()

