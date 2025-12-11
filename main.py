"""
EPUB转TXT批量转换工具主程序
"""
import os
import sys
import argparse
from pathlib import Path
from epub_parser import EpubParser
from text_splitter import TextSplitter


def find_epub_files(directory: str) -> list:
    """
    查找目录中的所有EPUB文件
    参数:
        directory: 目录路径
    返回:
        EPUB文件路径列表
    """
    epub_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith('.epub'):
                epub_files.append(os.path.join(root, file))
    return epub_files


def batch_convert(epub_files: list, output_dir: str = None, split_files: bool = True):
    """
    批量转换EPUB文件为TXT
    参数:
        epub_files: EPUB文件路径列表
        output_dir: 输出目录，如果为None则使用输入文件所在目录
        split_files: 是否根据字数分割文件
    """
    parser = EpubParser()
    splitter = TextSplitter()
    
    total_files = len(epub_files)
    print(f"找到 {total_files} 个EPUB文件\n")
    
    success_count = 0
    fail_count = 0
    
    for idx, epub_file in enumerate(epub_files, 1):
        print(f"[{idx}/{total_files}] 处理: {os.path.basename(epub_file)}")
        
        try:
            # 确定输出目录
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                base_name = os.path.splitext(os.path.basename(epub_file))[0]
                txt_output = os.path.join(output_dir, f"{base_name}.txt")
            else:
                txt_output = None  # 使用默认路径（与epub同目录）
            
            # 提取章节信息
            chapters = parser.extract_chapters(epub_file)
            
            if not chapters:
                print(f"  ✗ 无法提取章节信息")
                fail_count += 1
                continue
            
            # 统计总字数（只统计章节内容，不包括标题）
            total_words = sum(splitter.count_content_words(ch['content']) for ch in chapters)
            
            # 如果需要分割
            if split_files:
                split_count = splitter.calculate_split_count(total_words)
                
                if split_count > 1:
                    # 需要分割（使用新规则：按8万字在章节边界切分）
                    chapter_groups = splitter.split_by_word_count_at_chapter_boundary(chapters)
                    
                    # 确定输出目录
                    if output_dir:
                        output_dir_for_split = output_dir
                    else:
                        output_dir_for_split = os.path.dirname(epub_file)
                    
                    base_name = os.path.splitext(os.path.basename(epub_file))[0]
                    split_files_list = []
                    
                    # 生成分割后的文件
                    for i, group in enumerate(chapter_groups):
                        output_filename = f"{base_name}_part{i+1:02d}.txt"
                        output_path = os.path.join(output_dir_for_split, output_filename)
                        splitter.write_chapters_to_file(group, output_path)
                        split_files_list.append(output_path)
                    
                    # 合并字数过小的相邻文件（启用调试日志）
                    merged_files = splitter.merge_small_files(split_files_list, debug=True)
                    
                    print(f"  ✓ 转换完成，已分割为 {len(split_files_list)} 个文件")
                    if len(merged_files) < len(split_files_list):
                        print(f"  ✓ 合并后为 {len(merged_files)} 个文件（合并了 {len(split_files_list) - len(merged_files)} 个文件）")
                    print(f"    字数: {total_words:,}，章节数: {len(chapters)}")
                else:
                    # 不需要分割，直接生成TXT文件
                    txt_file = parser.convert_to_txt(epub_file, txt_output)
                    print(f"  ✓ 转换完成: {os.path.basename(txt_file)}")
                    print(f"    字数: {total_words:,}，章节数: {len(chapters)}，无需分割")
            else:
                # 不分割，直接转换
                txt_file = parser.convert_to_txt(epub_file, txt_output)
                print(f"  ✓ 转换完成: {os.path.basename(txt_file)}")
                print(f"    字数: {total_words:,}，章节数: {len(chapters)}")
            
            success_count += 1
        
        except Exception as e:
            print(f"  ✗ 处理失败: {e}")
            fail_count += 1
        
        print()
    
    # 统计信息
    print("=" * 60)
    print(f"处理完成!")
    print(f"成功: {success_count} 个")
    print(f"失败: {fail_count} 个")
    print("=" * 60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='EPUB转TXT批量转换工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 转换当前目录下的所有EPUB文件
  python main.py

  # 转换指定目录下的所有EPUB文件
  python main.py -d /path/to/epub/files

  # 转换指定文件
  python main.py -f file1.epub file2.epub

  # 指定输出目录
  python main.py -d /path/to/epub/files -o /path/to/output

  # 不分割文件（只转换，不分割）
  python main.py --no-split
        """
    )
    
    parser.add_argument(
        '-d', '--directory',
        type=str,
        help='包含EPUB文件的目录路径'
    )
    
    parser.add_argument(
        '-f', '--files',
        nargs='+',
        help='要转换的EPUB文件路径（可以指定多个）'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=str,
        help='输出目录路径（默认为输入文件所在目录）'
    )
    
    parser.add_argument(
        '--no-split',
        action='store_true',
        help='不分割文件（只转换，不根据字数分割）'
    )
    
    args = parser.parse_args()
    
    # 收集EPUB文件
    epub_files = []
    
    if args.files:
        # 使用指定的文件
        for file_path in args.files:
            if os.path.exists(file_path) and file_path.lower().endswith('.epub'):
                epub_files.append(file_path)
            else:
                print(f"警告: 文件不存在或不是EPUB格式: {file_path}")
    
    elif args.directory:
        # 从指定目录查找
        if os.path.isdir(args.directory):
            epub_files = find_epub_files(args.directory)
        else:
            print(f"错误: 目录不存在: {args.directory}")
            sys.exit(1)
    
    else:
        # 默认使用当前目录
        current_dir = os.getcwd()
        print(f"未指定目录或文件，使用当前目录: {current_dir}")
        epub_files = find_epub_files(current_dir)
    
    if not epub_files:
        print("错误: 未找到任何EPUB文件")
        sys.exit(1)
    
    # 执行批量转换
    batch_convert(epub_files, args.output, split_files=not args.no_split)


if __name__ == '__main__':
    main()

