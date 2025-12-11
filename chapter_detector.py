"""
章节识别规则库
支持多种常见的章节格式识别
增强版：支持装饰符号、空格、英文单词数字等更多格式，并减少误判
"""
import re
from typing import List, Tuple, Optional


class ChapterDetector:
    """章节检测器，使用正则表达式匹配各种章节格式"""
    
    def __init__(self):
        """初始化章节识别规则"""
        # 编译一个用于检测行末是否为句子结束标点的正则
        self.sentence_end_pattern = re.compile(r'[，。；,;]+$')
        self.patterns = self._build_patterns()
    
    def _build_patterns(self) -> List[Tuple[str, re.Pattern]]:
        """
        构建章节识别规则库（增强版）
        返回: [(规则名称, 正则表达式模式), ...]
        """
        patterns = []
        
        # 英文数字单词库（常用）
        eng_num_words = r'(One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten|Eleven|Twelve|Thirteen|Fourteen|Fifteen|Sixteen|Seventeen|Eighteen|Nineteen|Twenty|Thirty|Forty|Fifty|Sixty|Seventy|Eighty|Ninety|Hundred|First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth)'
        
        # --- 辅助正则片段 ---
        # 允许括号包裹：匹配 [ 【 ( （
        prefix_wrap = r'^[\[【\(\（\s]*'
        # 允许括号结束：匹配 ] 】 ) ） : ： 加上空格
        suffix_wrap = r'[\]】\)\）\:\：\s]*'
        # 允许内部有空格：第 一 章
        gap = r'\s*'
        
        # 中文章节格式（增强版：支持括号、空格）
        chinese_patterns = [
            # 第x章（支持括号、空格）
            (rf'{prefix_wrap}第{gap}[零一二三四五六七八九十百千万\d]+{gap}章{suffix_wrap}[^\n]*$', '第x章(增强)'),
            # 第x[节篇回卷部集册辑部分单元]（支持括号、空格）
            (rf'{prefix_wrap}第{gap}[零一二三四五六七八九十百千万\d]+{gap}[节篇回卷部集册辑部分单元]{suffix_wrap}[^\n]*$', '第x[单位](增强)'),
            
            # 不带"第"的格式（支持括号）
            (rf'{prefix_wrap}[零一二三四五六七八九十百千万\d]+{gap}[章节篇回卷部集册辑]{suffix_wrap}[^\n]*$', 'x[单位](增强)'),
            
            # 纯中文数字列表：一、 （一） 【一】 【二】
            (rf'{prefix_wrap}[零一二三四五六七八九十百千万]+{gap}[、．.）\)\]】]{suffix_wrap}[^\n]*$', '中文数字列表'),
            (rf'{prefix_wrap}[零一二三四五六七八九十百千万]+{gap}[、．.）\)\]】]{suffix_wrap}$', '中文数字列表(纯)'),
        ]
        
        # 英文章节格式（增强版：支持英文单词数字、冒号分隔）
        english_patterns = [
            # Chapter x, Chapter 1: Title, Chapter One
            (rf'^{prefix_wrap}(Chapter|Part|Section|Book|Volume){gap}[0-9IVXLC]+{suffix_wrap}[^\n]*$', 'English Numeric'),
            # 支持英文单词数字: Chapter One, Part First
            (rf'^{prefix_wrap}(Chapter|Part|Section|Book|Volume){gap}{eng_num_words}{suffix_wrap}[^\n]*$', 'English Word'),
            # 支持连字符: Chapter Twenty-Five
            (rf'^{prefix_wrap}(Chapter|Part){gap}({eng_num_words}[\s-]+)*{eng_num_words}{suffix_wrap}[^\n]*$', 'English Word Compound'),
        ]
        
        # 数字开头的章节（严格限制，防止误判年份）
        number_patterns = [
            # 纯数字开头（带点或空格，且有后续内容）
            (r'^\d+\.\s+[^\n]+$', '数字. 标题'),  # 1. Title
            (r'^\d+、[^\n]+$', '数字、标题'),      # 1、标题
            (r'^\d+）[^\n]+$', '数字）标题'),      # 1）标题
            (r'^\d+\)\s*[^\n]+$', '数字)标题'),   # 1) Title
            
            # 罗马数字开头
            (r'^[IVXLC]+\.\s+[^\n]+$', '罗马数字.标题'),
            (r'^[IVXLC]+\s+[^\n]+$', '罗马数字 标题'),
            
            # 中文数字开头（支持括号）
            (rf'{prefix_wrap}[一二三四五六七八九十]+{gap}[、．.）\)]{suffix_wrap}[^\n]+$', '中文数字列表标题'),
            (rf'{prefix_wrap}[零一二三四五六七八九十百千万]+{gap}[、．.）\)]{suffix_wrap}[^\n]+$', '完整中文数字列表标题'),
        ]
        
        # 特殊格式（增强版：添加番外、附录等）
        special_keywords = r'序言|前言|后记|楔子|尾声|引子|开场|终章|番外|番外篇|附录|致谢|结语|参考文献|参考文献|目录|索引'
        special_patterns = [
            # 特殊章节（支持括号）
            (rf'{prefix_wrap}({special_keywords})[^\n]*$', '特殊章节'),
            # 上中下（支持括号）
            (rf'{prefix_wrap}(上|中|下)[篇部卷]?{suffix_wrap}$', '分卷指示'),
            # 第一、第二等（支持括号）
            (rf'{prefix_wrap}第{gap}[一二三四五六七八九十]+{suffix_wrap}[^\n]*$', '第中文数字'),
            (rf'{prefix_wrap}第{gap}[0-9]+{suffix_wrap}[^\n]*$', '第数字'),
        ]
        
        # 组合所有模式（注意顺序：越具体的越前面）
        all_str_patterns = chinese_patterns + english_patterns + special_patterns + number_patterns
        
        # 编译正则表达式
        compiled_patterns = []
        for pattern_str, name in all_str_patterns:
            try:
                # 使用 IGNORECASE 和 MULTILINE
                compiled_patterns.append((name, re.compile(pattern_str, re.IGNORECASE | re.MULTILINE)))
            except re.error as e:
                print(f"警告: 正则表达式编译失败 {name}: {pattern_str}, 错误: {e}")
        
        return compiled_patterns
    
    def is_chapter_title(self, text: str) -> Optional[str]:
        """
        判断文本是否为章节标题（增强版：减少误判）
        参数:
            text: 要检查的文本
        返回:
            如果匹配到章节格式，返回匹配的规则名称；否则返回None
        """
        if not text or not isinstance(text, str):
            return None
        
        # 去除首尾空白
        text = text.strip()
        
        # 优化1: 长度过滤（标题通常较短，超过60字符大概率是正文段落开头）
        if len(text) > 60:
            return None
        
        # 先进行正则匹配
        matched_rule = None
        for name, pattern in self.patterns:
            if pattern.match(text):
                matched_rule = name
                break
        
        if not matched_rule:
            return None
        
        # 如果匹配成功，再进行误判过滤
        
        # 优化2: 句末标点过滤（防止误判正文）
        # 如果以逗号、句号结尾，且长度较长，可能是正文句子
        is_sentence = self.sentence_end_pattern.search(text)
        if is_sentence and len(text) > 15:
            # 特例：有些标题真的以感叹号或问号结尾，如 "第一章 谁是凶手？"
            # 但带逗号、句号的通常不是标题
            if text[-1] in ['，', '。', ',', '.']:
                return None
        
        # 优化3: 检查是否是明显的正文句子（包含动词、助词等）
        # 常见动词和助词
        common_verbs = ['的', '了', '在', '是', '有', '和', '与', '及', '写', '走', '看', '说', '想', '做', '来', '去', '到', '给', '让', '被', '把', '得', '很', '我', '你', '他', '她', '它', '们']
        verb_count = sum(1 for v in common_verbs if v in text)
        
        # 如果文本较长且包含多个常见动词/助词，可能是正文
        if len(text) > 20:
            # 如果包含3个或以上动词/助词，且长度>25，很可能是正文
            if verb_count >= 3 and len(text) > 25:
                return None
        elif len(text) > 12:
            # 对于较短的文本，如果包含明显的动作词（如"写"、"走"、"看"等），且后面跟着"得"、"很"等，可能是正文
            action_verbs = ['写', '走', '看', '说', '想', '做', '来', '去', '到', '给', '让', '被', '把', '喜欢', '讨厌', '觉得', '认为']
            has_action = any(v in text for v in action_verbs)
            has_modifier = any(m in text for m in ['得', '很', '非常', '特别', '十分'])
            # 如果包含动作词和修饰词，且长度>12，很可能是正文句子
            if has_action and has_modifier:
                return None
        
        # 优化4: 检查是否包含明显的句子结构（如"了...的"、"在...中"等）
        # 如果文本较长，且包含多个句子结构词，可能是完整句子而非标题
        if len(text) > 20:
            sentence_patterns = ['了', '的', '在', '中', '里', '上', '下', '着', '过']
            pattern_count = sum(1 for p in sentence_patterns if p in text)
            # 如果包含4个或以上句子结构词，且长度>25，很可能是正文
            if pattern_count >= 4 and len(text) > 25:
                return None
        
        return matched_rule
    
    def find_chapters(self, lines: List[str]) -> List[Tuple[int, str, str]]:
        """
        在文本行中查找所有章节标题
        参数:
            lines: 文本行列表
        返回:
            [(行号, 章节标题, 规则名称), ...]
        """
        chapters = []
        for idx, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            rule_name = self.is_chapter_title(line)
            if rule_name:
                chapters.append((idx, line, rule_name))
        
        return chapters


if __name__ == '__main__':
    # 测试代码（增强版测试用例）
    detector = ChapterDetector()
    
    test_titles = [
        # 基础格式
        "第一章 开始",
        "第1章 开始",
        "Chapter 1",
        "CHAPTER 1",
        "1. 第一章",
        "一、开始",
        "序言",
        "前言",
        "第10章 测试",
        "第100章 测试",
        "Part 1",
        "Section 2",
        "第一卷",
        "第一回",
        
        # 新增：装饰符号与括号
        "【第一章】 重生",
        "[第一章] 标题",
        "（第一章） 标题",
        "Chapter 1: The Beginning",
        
        # 新增：字符间空格
        "第  一  章 间隔",
        "第 1 章 测试",
        
        # 新增：英文单词数字
        "Chapter One",
        "Chapter Twenty-Five",
        "Part First",
        
        # 新增：更多特殊章节
        "番外篇：关于主角",
        "附录 A",
        "致谢",
        "结语",
        
        # 新增：中文数字列表
        "（一）背景介绍",
        "【二】发展",
        
        # 误判测试（应该被过滤）
        "第一章 他走进了房间，看着窗外的风景。",  # 长句+句号，应该被过滤
        "第一章写得很好，我很喜欢。",  # 正文句子，应该被过滤
        "Copyright 2023",  # 版权信息，应该忽略
        "2023年1月1日",  # 日期，应该忽略
    ]
    
    print("章节识别测试（增强版）:")
    print("=" * 70)
    for title in test_titles:
        result = detector.is_chapter_title(title)
        status = "✓" if result else "✗"
        result_str = result or "未识别"
        print(f"{status} [{result_str:20s}] : {title}")
    print("=" * 70)

