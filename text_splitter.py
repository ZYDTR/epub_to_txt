"""
文本分割模块
根据字数统计和分割规则，将文本分割成多个文件
"""
import os
from typing import List, Dict, Optional


class TextSplitter:
    """文本分割器"""
    
    # 每8万字对应一份（新的分割规则）
    WORDS_PER_PART = 80000
    
    def __init__(self):
        pass
    
    def count_words(self, text: str) -> int:
        """
        统计文本字数（纯文本内容，不包括格式标记）
        参数:
            text: 文本内容
        返回:
            字数（只统计实际文本字符，不包括换行、分隔线等格式字符）
        """
        if not text:
            return 0
        
        # 移除章节标题和分隔线等格式内容
        # 统计所有非空白字符（包括中文、英文、数字、标点等）
        # 但不包括换行符、制表符等空白字符
        total_chars = len([c for c in text if not c.isspace()])
        
        return total_chars
    
    def count_content_words(self, content_lines: List[str]) -> int:
        """
        统计章节内容字数（不包括章节标题和格式）
        参数:
            content_lines: 内容行列表
        返回:
            字数
        """
        if not content_lines:
            return 0
        
        # 只统计内容行，不包括标题和分隔线
        text = '\n'.join(content_lines)
        return self.count_words(text)
    
    def count_words_in_file(self, file_path: str) -> int:
        """
        统计文件字数（只统计实际内容，不包括章节标题和分隔线）
        参数:
            file_path: 文件路径
        返回:
            字数
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 过滤掉章节标题和分隔线
            content_lines = []
            skip_next = False
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                # 跳过分隔线
                if line.startswith('=') and len(line) >= 20:
                    skip_next = True
                    continue
                # 跳过章节标题（如果上一行是分隔线）
                if skip_next:
                    skip_next = False
                    continue
                content_lines.append(line)
            
            # 统计内容字数
            text = '\n'.join(content_lines)
            return self.count_words(text)
        except Exception as e:
            print(f"读取文件失败 {file_path}: {e}")
            return 0
    
    def calculate_split_count(self, word_count: int) -> int:
        """
        根据字数计算需要分割的份数
        参数:
            word_count: 总字数
        返回:
            分割份数（至少为1）
        """
        if word_count < self.WORDS_PER_PART:
            return 1
        
        # 每8万字增加一份
        parts = (word_count // self.WORDS_PER_PART) + 1
        return parts
    
    def split_by_chapters(self, chapters: List[Dict], split_count: int) -> List[List[Dict]]:
        """
        按照章节分割文本（新规则：按8万字切分，切分点必须在章节边界）
        参数:
            chapters: 章节列表，每个章节包含 {'title': 标题, 'content': 内容行列表}
            split_count: 分割份数（用于兼容旧代码，实际不使用）
        返回:
            分割后的章节组列表
        """
        if len(chapters) == 0:
            return []
        
        # 新规则：按8万字切分，切分点必须在章节边界
        result = []
        current_chapters = []
        current_words = 0
        target_words = self.WORDS_PER_PART  # 8万字
        
        for chapter in chapters:
            chapter_content = '\n'.join(chapter['content'])
            chapter_words = self.count_words(chapter_content)
            
            # 如果当前累计字数加上本章字数会超过目标字数
            if current_words + chapter_words > target_words and current_chapters:
                # 需要切分
                # 检查当前累计字数是否接近目标（允许一定误差）
                if current_words >= target_words * 0.7:  # 至少达到目标的70%
                    # 保存当前部分
                    result.append(current_chapters.copy())
                    current_chapters = []
                    current_words = 0
                
                # 如果单个章节就超过目标字数，也要切分
                if chapter_words > target_words:
                    # 如果当前有未保存的章节，先保存
                    if current_chapters:
                        result.append(current_chapters.copy())
                        current_chapters = []
                        current_words = 0
                    # 这个章节单独成一份
                    result.append([chapter])
                    continue
            
            # 添加当前章节
            current_chapters.append(chapter)
            current_words += chapter_words
        
        # 保存最后的部分
        if current_chapters:
            result.append(current_chapters)
        
        return result
    
    def split_by_word_count_at_chapter_boundary(self, chapters: List[Dict]) -> List[List[Dict]]:
        """
        按照字数在章节边界切分（新规则）
        从开头开始，每8万字找一个最近的章节边界作为切分点
        参数:
            chapters: 章节列表，每个章节包含 {'title': 标题, 'content': 内容行列表}
        返回:
            分割后的章节组列表
        """
        if len(chapters) == 0:
            return []
        
        result = []
        target_words = self.WORDS_PER_PART  # 8万字
        current_chapters = []
        current_words = 0
        chapter_idx = 0
        
        while chapter_idx < len(chapters):
            chapter = chapters[chapter_idx]
            chapter_content = '\n'.join(chapter['content'])
            chapter_words = self.count_words(chapter_content)
            
            # 累计字数
            new_total_words = current_words + chapter_words
            
            # 如果累计字数达到或超过目标字数
            if new_total_words >= target_words:
                # 计算超出多少
                overflow = new_total_words - target_words
                
                # 判断向前还是向后找章节边界更近
                # 向前：当前累计字数（到上一章结尾）
                # 向后：新累计字数（到当前章结尾）
                distance_before = current_words  # 到上一章结尾的距离
                distance_after = new_total_words  # 到当前章结尾的距离
                
                # 计算到目标字数的距离
                dist_to_target_before = abs(target_words - distance_before)
                dist_to_target_after = abs(target_words - distance_after)
                
                # 选择更接近目标字数的章节边界
                if dist_to_target_before <= dist_to_target_after and current_chapters:
                    # 向前切分：在当前章节之前切分
                    result.append(current_chapters.copy())
                    current_chapters = [chapter]
                    current_words = chapter_words
                    chapter_idx += 1
                else:
                    # 向后切分：包含当前章节，然后切分
                    current_chapters.append(chapter)
                    result.append(current_chapters.copy())
                    current_chapters = []
                    current_words = 0
                    chapter_idx += 1
            else:
                # 还没达到目标字数，继续添加章节
                current_chapters.append(chapter)
                current_words = new_total_words
                chapter_idx += 1
        
        # 保存最后的部分
        if current_chapters:
            result.append(current_chapters)
        
        return result
    
    def write_chapters_to_file(self, chapters: List[Dict], output_path: str):
        """
        将章节列表写入文件
        参数:
            chapters: 章节列表
            output_path: 输出文件路径
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            for chapter in chapters:
                f.write(f"\n{chapter['title']}\n")
                f.write("=" * 50 + "\n\n")
                for line in chapter['content']:
                    f.write(line + "\n")
                f.write("\n")
    
    def merge_small_files(self, file_list: List[str], min_words_per_file: int = None, debug: bool = False, log_callback=None) -> List[str]:
        """
        合并字数过小的相邻文件（递归合并）
        规则：
        1. 如果相邻文件相加字数少于10万字，就合并（递归）
        2. 如果某个文件小于1万字，找它相邻的更小的文件合并（递归）
        
        参数:
            file_list: 文件路径列表
            min_words_per_file: 最小字数阈值（默认10万字）
            debug: 是否输出调试信息
            log_callback: 日志回调函数，用于将调试信息输出到GUI（可选）
        参数:
            file_list: 文件路径列表（按顺序）
            min_words_per_file: 每个文件的最小字数阈值，默认10万字
            debug: 是否输出调试信息
        返回:
            合并后的文件路径列表
        """
        if min_words_per_file is None:
            min_words_per_file = 100000  # 10万字
        
        if len(file_list) <= 1:
            return file_list
        
        SMALL_FILE_THRESHOLD = 10000  # 1万字
        
        # 递归合并，直到没有更多需要合并的文件
        max_iterations = 100  # 防止无限循环
        iteration = 0
        current_files = file_list.copy()
        
        # 辅助函数：同时输出到终端和GUI
        def debug_log(msg):
            if debug:
                print(msg)
                if log_callback:
                    log_callback(msg + '\n')
        
        debug_log(f"\n开始合并文件，共 {len(current_files)} 个文件")
        
        while iteration < max_iterations:
            iteration += 1
            changed = False
            
            debug_log(f"\n--- 第 {iteration} 轮合并 ---")
            
            # 统计当前文件的字数（只统计存在的文件）
            file_words = []
            for file_path in current_files:
                # 验证文件是否存在（合并后可能已被删除）
                if not os.path.exists(file_path):
                    debug_log(f"  警告: 文件不存在，跳过: {os.path.basename(file_path)}")
                    continue
                try:
                    words = self.count_words_in_file(file_path)
                    file_words.append((file_path, words))
                    debug_log(f"  文件: {os.path.basename(file_path)} = {words:,} 字")
                except Exception as e:
                    debug_log(f"  错误: 读取文件失败 {file_path}: {e}")
                    continue
            
            # 第一步：合并小于1万字的文件（找相邻的更小的文件合并）
            new_file_words = []
            i = 0
            
            debug_log(f"\n规则2: 合并小于 {SMALL_FILE_THRESHOLD:,} 字的文件")
            
            while i < len(file_words):
                current_file, current_words = file_words[i]
                file_name = os.path.basename(current_file)
                
                # 如果当前文件小于1万字
                if current_words < SMALL_FILE_THRESHOLD:
                    debug_log(f"  发现小文件: {file_name} ({current_words:,} 字) < {SMALL_FILE_THRESHOLD:,} 字")
                    
                    # 找相邻的文件合并（优先选择更小的，如果没有更小的，合并到下一个）
                    merged = False
                    
                    # 检查前一个和后一个文件
                    prev_available = i > 0
                    next_available = i < len(file_words) - 1
                    prev_file = prev_words = None
                    next_file = next_words = None
                    
                    if prev_available:
                        prev_file, prev_words = file_words[i - 1]
                    if next_available:
                        next_file, next_words = file_words[i + 1]
                    
                    # 决定合并方向：优先选择更小的相邻文件
                    merge_to_prev = False
                    merge_to_next = False
                    
                    if prev_available and next_available:
                        # 两个方向都可用，选择更小的
                        if prev_words < next_words:
                            merge_to_prev = True
                        else:
                            merge_to_next = True
                    elif prev_available:
                        # 只有前一个可用
                        merge_to_prev = True
                    elif next_available:
                        # 只有后一个可用
                        merge_to_next = True
                    
                    # 执行合并（先验证文件是否存在）
                    if merge_to_prev:
                        # 合并到前一个文件
                        prev_name = os.path.basename(prev_file)
                        # 验证文件是否存在
                        if not os.path.exists(prev_file) or not os.path.exists(current_file):
                            missing = []
                            if not os.path.exists(prev_file):
                                missing.append(prev_name)
                            if not os.path.exists(current_file):
                                missing.append(file_name)
                            debug_log(f"    ⚠ 文件不存在，跳过合并: {', '.join(missing)}")
                            # 如果当前文件存在，保留它
                            if os.path.exists(current_file):
                                new_file_words.append((current_file, current_words))
                            i += 1
                            continue
                        
                        debug_log(f"    → 合并到前一个文件 {prev_name} ({prev_words:,} 字)")
                        merged_file_path = self._merge_files([prev_file, current_file], current_files[0] if current_files else None)
                        merged_words = prev_words + current_words
                        # 替换前一个文件
                        new_file_words[-1] = (merged_file_path, merged_words)
                        merged = True
                        changed = True
                        debug_log(f"    ✓ 合并后: {os.path.basename(merged_file_path)} ({merged_words:,} 字)")
                    
                    elif merge_to_next:
                        # 合并到当前文件（与下一个文件合并）
                        next_name = os.path.basename(next_file)
                        # 验证文件是否存在
                        if not os.path.exists(current_file) or not os.path.exists(next_file):
                            missing = []
                            if not os.path.exists(current_file):
                                missing.append(file_name)
                            if not os.path.exists(next_file):
                                missing.append(next_name)
                            debug_log(f"    ⚠ 文件不存在，跳过合并: {', '.join(missing)}")
                            # 如果当前文件存在，保留它
                            if os.path.exists(current_file):
                                new_file_words.append((current_file, current_words))
                            i += 1
                            continue
                        
                        debug_log(f"    → 合并到后一个文件 {next_name} ({next_words:,} 字)")
                        merged_file_path = self._merge_files([current_file, next_file], current_files[0] if current_files else None)
                        merged_words = current_words + next_words
                        new_file_words.append((merged_file_path, merged_words))
                        i += 2  # 跳过下一个文件
                        merged = True
                        changed = True
                        debug_log(f"    ✓ 合并后: {os.path.basename(merged_file_path)} ({merged_words:,} 字)")
                    
                    # 如果无法合并（理论上不应该发生，因为至少有一个相邻文件）
                    if not merged:
                        debug_log(f"    ⚠ 无法合并（没有相邻文件），保留文件: {file_name} ({current_words:,} 字)")
                        new_file_words.append((current_file, current_words))
                        i += 1
                else:
                    # 文件足够大，直接保留
                    if debug and current_words < min_words_per_file:
                        debug_log(f"  文件足够大: {file_name} ({current_words:,} 字) >= {SMALL_FILE_THRESHOLD:,} 字")
                    new_file_words.append((current_file, current_words))
                    i += 1
            
            # 如果第一步有变化，更新文件列表并继续
            if changed:
                debug_log(f"  规则2有变化，更新文件列表，继续下一轮")
                debug_log(f"  更新后的文件列表:")
                for f_path, f_words in new_file_words:
                    debug_log(f"    {os.path.basename(f_path)}: {f_words:,} 字")
                # 更新文件列表为合并后的新文件
                current_files = [f[0] for f in new_file_words]
                # 验证文件是否存在
                valid_files = []
                for f_path in current_files:
                    if os.path.exists(f_path):
                        valid_files.append(f_path)
                    else:
                        debug_log(f"  警告: 文件不存在，跳过: {os.path.basename(f_path)}")
                current_files = valid_files
                continue
            
            # 第二步：合并相邻文件，如果相加少于10万字
            debug_log(f"\n规则1: 合并相邻文件，如果相加少于 {min_words_per_file:,} 字")
            
            final_files = []
            i = 0
            
            while i < len(file_words):
                current_files_to_merge = [file_words[i][0]]  # 当前要合并的文件列表
                current_words = file_words[i][1]    # 当前累计字数
                current_name = os.path.basename(file_words[i][0])
                
                debug_log(f"  处理文件: {current_name} ({current_words:,} 字)")
                
                # 尝试合并后续文件，直到累计字数达到阈值
                j = i + 1
                while j < len(file_words) and current_words < min_words_per_file:
                    # 如果加上下一个文件仍然小于阈值，继续合并
                    next_file, next_words = file_words[j]
                    next_name = os.path.basename(next_file)
                    combined_words = current_words + next_words
                    
                    if combined_words < min_words_per_file:
                        debug_log(f"    → 加上 {next_name} ({next_words:,} 字) = {combined_words:,} 字 < {min_words_per_file:,} 字，继续合并")
                        current_files_to_merge.append(next_file)
                        current_words = combined_words
                        j += 1
                    else:
                        debug_log(f"    → 加上 {next_name} ({next_words:,} 字) = {combined_words:,} 字 >= {min_words_per_file:,} 字，停止合并")
                        break
                
                # 如果只有一个文件且字数足够，直接保留
                if len(current_files_to_merge) == 1 and current_words >= min_words_per_file:
                    debug_log(f"    ✓ 文件足够大，保留: {current_name} ({current_words:,} 字)")
                    final_files.append(current_files_to_merge[0])
                else:
                    # 需要合并多个文件
                    merged_file_path = self._merge_files(current_files_to_merge, current_files[0] if current_files else None)
                    merged_name = os.path.basename(merged_file_path)
                    file_names = [os.path.basename(f) for f in current_files_to_merge]
                    debug_log(f"    ✓ 合并 {len(current_files_to_merge)} 个文件: {', '.join(file_names)}")
                    debug_log(f"    → 合并后: {merged_name} ({current_words:,} 字)")
                    final_files.append(merged_file_path)
                    # 如果合并后仍然小于阈值，标记为需要继续处理
                    if current_words < min_words_per_file:
                        debug_log(f"    ⚠ 合并后仍然小于 {min_words_per_file:,} 字，标记为需要继续处理")
                        changed = True
                
                i = j
            
            # 如果第二步有变化，继续递归
            if changed:
                debug_log(f"  规则1有变化，继续下一轮递归")
                debug_log(f"  更新后的文件列表:")
                for f_path in final_files:
                    if os.path.exists(f_path):
                        words = self.count_words_in_file(f_path)
                        debug_log(f"    {os.path.basename(f_path)}: {words:,} 字")
                    else:
                        debug_log(f"    警告: 文件不存在: {os.path.basename(f_path)}")
                # 验证文件是否存在（合并后原始文件可能已被删除）
                valid_files = []
                for f_path in final_files:
                    if os.path.exists(f_path):
                        valid_files.append(f_path)
                    else:
                        debug_log(f"  警告: 文件不存在，跳过: {os.path.basename(f_path)}")
                if len(valid_files) != len(final_files):
                    debug_log(f"  警告: {len(final_files) - len(valid_files)} 个文件不存在，已过滤")
                current_files = valid_files
                continue
            else:
                # 没有更多变化，返回结果
                debug_log(f"\n合并完成，最终 {len(final_files)} 个文件")
                for f in final_files:
                    words = self.count_words_in_file(f)
                    debug_log(f"  {os.path.basename(f)}: {words:,} 字")
                return final_files
        
        # 如果达到最大迭代次数，返回当前结果
        return current_files
    
    def _merge_files(self, file_paths: List[str], reference_file: str = None) -> str:
        """
        合并多个文件为一个文件
        参数:
            file_paths: 要合并的文件路径列表
            reference_file: 参考文件路径（用于确定输出目录和命名）
        返回:
            合并后的文件路径
        """
        if not file_paths:
            return None
        
        if len(file_paths) == 1:
            return file_paths[0]
        
        # 确定输出文件路径
        if reference_file:
            ref_dir = os.path.dirname(reference_file)
            ref_base = os.path.splitext(os.path.basename(reference_file))[0]
            # 去掉_partXX后缀
            if '_part' in ref_base:
                ref_base = ref_base.rsplit('_part', 1)[0]
        else:
            ref_dir = os.path.dirname(file_paths[0])
            ref_base = os.path.splitext(os.path.basename(file_paths[0]))[0]
            if '_part' in ref_base:
                ref_base = ref_base.rsplit('_part', 1)[0]
        
        # 生成合并后的文件名
        # 找到第一个和最后一个文件的part编号
        first_part = None
        last_part = None
        for file_path in file_paths:
            basename = os.path.basename(file_path)
            if '_part' in basename:
                try:
                    part_num = int(basename.split('_part')[1].split('.')[0])
                    if first_part is None:
                        first_part = part_num
                    last_part = part_num
                except:
                    pass
        
        if first_part is not None and last_part is not None:
            if first_part == last_part:
                merged_filename = f"{ref_base}_part{first_part:02d}.txt"
            else:
                merged_filename = f"{ref_base}_part{first_part:02d}-{last_part:02d}.txt"
        else:
            merged_filename = f"{ref_base}_merged.txt"
        
        merged_file_path = os.path.join(ref_dir, merged_filename)
        
        # 读取并合并文件内容
        all_content = []
        for file_path in file_paths:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    all_content.append(content)
            except Exception as e:
                print(f"读取文件失败 {file_path}: {e}")
        
        # 写入合并后的文件
        with open(merged_file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(all_content))
        
        # 删除原始文件
        for file_path in file_paths:
            try:
                if file_path != merged_file_path and os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"删除文件失败 {file_path}: {e}")
        
        return merged_file_path
    
    def split_file(self, input_file: str, output_dir: Optional[str] = None) -> List[str]:
        """
        分割TXT文件
        参数:
            input_file: 输入TXT文件路径
            output_dir: 输出目录，如果为None则使用输入文件所在目录
        返回:
            输出文件路径列表
        """
        if output_dir is None:
            output_dir = os.path.dirname(input_file)
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 读取文件并解析章节
        chapters = self._parse_chapters_from_file(input_file)
        
        if not chapters:
            print(f"无法解析章节: {input_file}")
            return []
        
        # 统计总字数
        total_words = sum(self.count_words('\n'.join(ch['content'])) for ch in chapters)
        
        # 计算分割份数
        split_count = self.calculate_split_count(total_words)
        
        print(f"文件: {os.path.basename(input_file)}")
        print(f"总字数: {total_words:,}")
        print(f"章节数: {len(chapters)}")
        print(f"分割份数: {split_count}")
        
        if split_count == 1:
            # 不需要分割
            return [input_file]
        
        # 分割章节
        chapter_groups = self.split_by_chapters(chapters, split_count)
        
        # 生成输出文件
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        output_files = []
        
        for i, group in enumerate(chapter_groups):
            output_filename = f"{base_name}_part{i+1:02d}.txt"
            output_path = os.path.join(output_dir, output_filename)
            
            # 写入文件
            self.write_chapters_to_file(group, output_path)
            
            output_files.append(output_path)
            print(f"  生成: {output_filename} (章节 {len(group)} 个)")
        
        return output_files
    
    def _parse_chapters_from_file(self, file_path: str) -> List[Dict]:
        """
        从TXT文件中解析章节
        参数:
            file_path: 文件路径
        返回:
            章节列表
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"读取文件失败 {file_path}: {e}")
            return []
        
        chapters = []
        current_chapter = None
        current_content = []
        
        for line in lines:
            line = line.rstrip('\n\r')
            
            # 检查是否是章节标题（以等号分隔线为标志）
            if line.strip() == '=' * 50 or line.strip() == '=' * len(line.strip()):
                # 遇到分隔线，说明之前的内容是章节标题
                if current_chapter is not None and current_content:
                    # 保存上一章
                    chapters.append({
                        'title': current_chapter,
                        'content': current_content
                    })
                    current_content = []
                
                # 读取下一行作为章节标题
                continue
            
            # 检查是否是章节标题（简单判断：单独一行且较短）
            stripped = line.strip()
            if stripped and len(stripped) < 100 and not stripped.startswith('='):
                # 可能是章节标题，但需要进一步确认
                # 这里简化处理：如果当前没有章节，或者上一行是空行，可能是新章节
                if current_chapter is None or (current_content and not current_content[-1].strip()):
                    if current_chapter is not None:
                        # 保存上一章
                        chapters.append({
                            'title': current_chapter,
                            'content': current_content
                        })
                    current_chapter = stripped
                    current_content = []
                    continue
            
            # 普通内容行
            if current_chapter is None:
                current_chapter = '前言'
            current_content.append(line)
        
        # 保存最后一章
        if current_chapter:
            chapters.append({
                'title': current_chapter,
                'content': current_content
            })
        
        return chapters


if __name__ == '__main__':
    # 测试代码
    splitter = TextSplitter()
    
    # 测试字数统计
    test_text = "这是一个测试文本。This is a test text. 123456"
    word_count = splitter.count_words(test_text)
    print(f"测试文本字数: {word_count}")
    
    # 测试分割计算
    test_counts = [50000, 150000, 250000, 350000, 500000]
    for count in test_counts:
        parts = splitter.calculate_split_count(count)
        print(f"字数 {count:,} -> 分割 {parts} 份")

