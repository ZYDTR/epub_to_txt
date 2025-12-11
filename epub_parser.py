"""
EPUB文件解析模块
提取epub文件中的文本内容
使用EPUB的TOC（目录）来识别章节
"""
import os
import zipfile
import re
import warnings
from typing import List, Optional, Dict, Tuple
from bs4 import BeautifulSoup
import ebooklib
from ebooklib import epub
from chapter_detector import ChapterDetector

# 抑制ebooklib的警告
warnings.filterwarnings('ignore', category=UserWarning, module='ebooklib')
warnings.filterwarnings('ignore', category=FutureWarning, module='ebooklib')


class EpubParser:
    """EPUB文件解析器"""
    
    def __init__(self):
        self.chapter_detector = ChapterDetector()
    
    def get_toc(self, epub_path: str) -> List[Tuple[str, str]]:
        """
        从EPUB文件中获取目录（TOC）
        参数:
            epub_path: EPUB文件路径
        返回:
            [(章节标题, 文件路径), ...]
        """
        try:
            # 使用ignore_ncx=True来避免警告
            book = epub.read_epub(epub_path, options={'ignore_ncx': False})
            toc = []
            
            # 获取目录结构
            def process_toc_item(item, level=0):
                """递归处理TOC项"""
                if isinstance(item, tuple):
                    # ebooklib的TOC项格式：(section, href, title, play_order)
                    if len(item) >= 3:
                        section = item[0] if len(item) > 0 else None
                        href = item[1] if len(item) > 1 else ''
                        title = item[2] if len(item) > 2 else ''
                        
                        # 只添加有标题和链接的项
                        if title and href:
                            # 使用章节识别规则判断是否是真正的章节标题
                            # 如果匹配章节格式（如"第一章"、"Chapter 1"等），说明指向正文
                            is_chapter = self.chapter_detector.is_chapter_title(title)
                            if is_chapter:
                                # 是章节标题，添加到TOC
                                toc.append((title, href))
                            # 如果不是章节标题（可能是目录页、版权页等），跳过
                        
                        # 处理子项
                        if section:
                            for sub_item in section:
                                process_toc_item(sub_item, level + 1)
                elif isinstance(item, list):
                    # 列表项
                    for sub_item in item:
                        process_toc_item(sub_item, level + 1)
            
            # 获取book的TOC
            book_toc = book.toc
            if book_toc:
                for item in book_toc:
                    process_toc_item(item)
            
            return toc
        
        except Exception as e:
            print(f"获取TOC失败 {epub_path}: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def parse(self, epub_path: str) -> List[str]:
        """
        解析EPUB文件，提取文本内容
        参数:
            epub_path: EPUB文件路径
        返回:
            文本行列表
        """
        try:
            book = epub.read_epub(epub_path)
            all_lines = []
            
            # 遍历所有章节
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    content = item.get_content()
                    if content:
                        soup = BeautifulSoup(content, 'html.parser')
                        text = self._extract_text(soup)
                        if text:
                            # 按行分割并过滤空行
                            lines = [line.strip() for line in text.split('\n') if line.strip()]
                            all_lines.extend(lines)
            
            return all_lines
        
        except Exception as e:
            print(f"解析EPUB文件失败 {epub_path}: {e}")
            return []
    
    def _extract_text(self, soup: BeautifulSoup) -> str:
        """
        从BeautifulSoup对象中提取纯文本
        参数:
            soup: BeautifulSoup对象
        返回:
            提取的文本
        """
        # 移除script和style标签
        for script in soup(["script", "style"]):
            script.decompose()
        
        # 获取文本
        text = soup.get_text()
        
        # 清理文本：合并多个空白字符
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
    
    def extract_chapters(self, epub_path: str) -> List[dict]:
        """
        提取EPUB文件中的章节（使用TOC目录）
        参数:
            epub_path: EPUB文件路径
        返回:
            章节列表，每个章节包含: {'title': 标题, 'content': 内容行列表}
        """
        try:
            # 使用ignore_ncx=False来避免警告（虽然会有警告，但功能正常）
            book = epub.read_epub(epub_path, options={'ignore_ncx': False})
            
            # 获取TOC目录（已使用章节识别规则过滤，只保留真正的章节标题）
            toc_items = self.get_toc(epub_path)
            
            if not toc_items:
                # 如果没有找到章节标题，回退到原来的方法（从文本中识别章节）
                print(f"警告: TOC中没有找到章节标题，回退到文本识别方法")
                return self._extract_chapters_from_text(epub_path)
            
            # 创建文件路径到内容的映射
            file_content_map = {}
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    file_name = item.get_name()
                    content = item.get_content()
                    if content:
                        soup = BeautifulSoup(content, 'html.parser')
                        text = self._extract_text(soup)
                        if text:
                            # 按行分割并过滤空行
                            lines = [line.strip() for line in text.split('\n') if line.strip()]
                            file_content_map[file_name] = lines
            
            # 根据TOC提取章节
            chapters = []
            used_files = {}  # 记录文件到章节的映射，避免重复使用
            
            # 最小内容长度阈值（如果文件内容少于这个值，可能是标题页，需要合并）
            MIN_CONTENT_LINES = 10
            MIN_CONTENT_CHARS = 100  # 最少字符数
            
            for i, (title, href) in enumerate(toc_items):
                # 解析href，获取文件名
                # href可能是相对路径，如 "chapter1.xhtml" 或 "OEBPS/chapter1.xhtml" 或完整URL
                file_name = href.split('#')[0]  # 去掉锚点
                # 去掉URL前缀（如果有）
                if '://' in file_name:
                    file_name = file_name.split('://')[-1]
                # 标准化路径分隔符
                file_name = file_name.replace('\\', '/')
                # 只取文件名部分（去掉路径）
                base_file_name = os.path.basename(file_name)
                
                # 查找对应的文件内容
                content_lines = []
                matched_file = None
                
                # 优先精确匹配
                for fname, lines in file_content_map.items():
                    fname_base = os.path.basename(fname)
                    # 精确匹配文件名
                    if fname_base == base_file_name or fname_base == file_name:
                        matched_file = fname
                        content_lines = lines
                        break
                
                # 如果没找到，尝试部分匹配
                if not content_lines:
                    for fname, lines in file_content_map.items():
                        if base_file_name in fname or file_name in fname:
                            matched_file = fname
                            content_lines = lines
                            break
                
                # 如果找到了内容
                if content_lines and matched_file:
                    # 计算内容字符数
                    content_text = '\n'.join(content_lines)
                    content_chars = len([c for c in content_text if not c.isspace()])
                    
                    # 检查内容是否足够（可能只是标题页）
                    is_short_content = len(content_lines) < MIN_CONTENT_LINES or content_chars < MIN_CONTENT_CHARS
                    
                    # 如果文件已经被使用过，合并内容
                    if matched_file in used_files:
                        # 合并到已有章节
                        existing_idx = used_files[matched_file]
                        chapters[existing_idx]['content'].extend(content_lines)
                    elif is_short_content:
                        # 内容太少，可能是标题页，尝试合并到上一个章节
                        if chapters:
                            # 合并到最后一个章节
                            chapters[-1]['content'].extend(content_lines)
                        else:
                            # 没有之前的章节，创建新章节
                            chapters.append({
                                'title': title,
                                'content': content_lines
                            })
                            used_files[matched_file] = len(chapters) - 1
                    else:
                        # 内容足够，创建新章节
                        chapters.append({
                            'title': title,
                            'content': content_lines
                        })
                        used_files[matched_file] = len(chapters) - 1
                else:
                    # 如果TOC中的文件找不到，记录警告但继续处理
                    if not matched_file:
                        print(f"警告: 无法找到TOC中引用的文件: {file_name} (标题: {title})")
            
            # 如果没有找到章节，回退到原来的方法
            if not chapters:
                return self._extract_chapters_from_text(epub_path)
            
            # 检查章节质量：如果大部分章节内容都很短，说明TOC可能不准确，回退到文本识别方法
            short_chapter_count = 0
            total_content_chars = 0
            
            for chapter in chapters:
                content_text = '\n'.join(chapter['content'])
                content_chars = len([c for c in content_text if not c.isspace()])
                total_content_chars += content_chars
                if content_chars < MIN_CONTENT_CHARS:
                    short_chapter_count += 1
            
            # 如果超过50%的章节内容很短，或者平均每章少于200字符，说明TOC不准确
            if len(chapters) > 0:
                short_ratio = short_chapter_count / len(chapters)
                avg_chars = total_content_chars / len(chapters) if len(chapters) > 0 else 0
                
                if short_ratio > 0.5 or avg_chars < 200:
                    print(f"警告: TOC章节内容过短（{short_ratio:.1%}章节短于{MIN_CONTENT_CHARS}字符，平均{avg_chars:.0f}字符），回退到文本识别方法")
                    return self._extract_chapters_from_text(epub_path)
            
            return chapters
        
        except Exception as e:
            print(f"提取章节失败 {epub_path}: {e}")
            # 回退到原来的方法
            return self._extract_chapters_from_text(epub_path)
    
    def _extract_chapters_from_text(self, epub_path: str) -> List[dict]:
        """
        从文本中提取章节（备用方法）
        参数:
            epub_path: EPUB文件路径
        返回:
            章节列表
        """
        lines = self.parse(epub_path)
        if not lines:
            return []
        
        # 查找所有章节标题
        chapter_positions = self.chapter_detector.find_chapters(lines)
        
        if not chapter_positions:
            # 如果没有找到章节标题，将整个内容作为一个章节
            return [{
                'title': '全文',
                'content': lines
            }]
        
        chapters = []
        
        # 提取每个章节的内容
        for i, (line_idx, title, rule_name) in enumerate(chapter_positions):
            # 确定章节内容的结束位置
            if i + 1 < len(chapter_positions):
                next_line_idx = chapter_positions[i + 1][0]
                content = lines[line_idx + 1:next_line_idx]  # 跳过标题行
            else:
                # 最后一章，包含到文件末尾
                content = lines[line_idx + 1:]
            
            chapters.append({
                'title': title,
                'content': content
            })
        
        return chapters
    
    def convert_to_txt(self, epub_path: str, output_path: Optional[str] = None) -> str:
        """
        将EPUB文件转换为TXT文件
        参数:
            epub_path: EPUB文件路径
            output_path: 输出TXT文件路径，如果为None则自动生成
        返回:
            输出文件路径
        """
        chapters = self.extract_chapters(epub_path)
        
        if output_path is None:
            base_name = os.path.splitext(os.path.basename(epub_path))[0]
            output_dir = os.path.dirname(epub_path)
            output_path = os.path.join(output_dir, f"{base_name}.txt")
        
        # 写入TXT文件
        with open(output_path, 'w', encoding='utf-8') as f:
            for chapter in chapters:
                # 写入章节标题
                f.write(f"\n{chapter['title']}\n")
                f.write("=" * 50 + "\n\n")
                
                # 写入章节内容
                for line in chapter['content']:
                    f.write(line + "\n")
                f.write("\n")
        
        return output_path


if __name__ == '__main__':
    # 测试代码
    parser = EpubParser()
    
    # 测试文件路径（需要用户提供）
    test_file = "test.epub"
    if os.path.exists(test_file):
        txt_path = parser.convert_to_txt(test_file)
        print(f"转换完成: {txt_path}")
    else:
        print("请提供测试EPUB文件")

