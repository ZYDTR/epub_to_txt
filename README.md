# EPUB转TXT批量转换工具

该项目用于你有一堆.epub格式的电子书想要进行批量处理，把它们变成.txt的同时，把书的前言、译者序、后记等等这些内容给剔除掉的，只把书的正文内容给保留（这一步为了不用无关信息干扰AI和节省token）。
接下来用于为喂AI进行知识问答或者生成演示文稿等。
例如遇到NotebokeLM需要控制复制文本进去的字数上限，所以将字数比较大的书进行智能切分，###按章节尽量平均切分从而保证语义。

## 功能特性

### 1. 批量转换
- 支持批量处理多个EPUB文件
- 自动识别目录中的所有EPUB文件
- 支持命令行参数指定文件或目录

<img width="1800" height="1456" alt="image" src="https://github.com/user-attachments/assets/2521d4da-a56c-47f4-bba7-a46f2e4edf11" />




### 2. 智能章节识别（增强版）
内置强大的章节识别规则库，支持多种常见的章节格式，并具备误判过滤功能：

**中文章节格式：**
- 第x章、第x篇、第x节、第x回、第x卷、第x部、第x集、第x册、第x辑等
- 支持中文数字（一、二、三...）和阿拉伯数字
- 支持不带"第"字的格式（如"一章"、"一篇"等）
- **新增：** 支持装饰符号包裹：`【第一章】`、`[第一章]`、`（第一章）`
- **新增：** 支持字符间空格：`第  一  章`、`第 1 章`（排版对齐）

**英文章节格式：**
- Chapter x、CHAPTER x
- Part x、PART x
- Section x、SECTION x
- Book x、BOOK x
- Volume x、VOLUME x
- 支持罗马数字（I、II、III...）
- **新增：** 支持英文单词数字：`Chapter One`、`Chapter Twenty-Five`、`Part First`
- **新增：** 支持冒号分隔：`Chapter 1: The Beginning`

**数字开头格式：**
- 1. 标题、1 标题、1、标题、1）标题
- 罗马数字开头
- 中文数字开头（一、二、三...）
- **新增：** 支持括号包裹：`（一）背景`、`【二】发展`

**特殊格式：**
- 序言、前言、后记、楔子、尾声、引子等
- 上、中、下、上篇、中篇、下篇等
- **新增：** 番外、番外篇、附录、致谢、结语、参考文献等

**误判过滤机制：**
- 自动过滤正文句子（如"第一章写得很好，我很喜欢。"）
- 自动过滤版权信息、日期等非章节内容
- 长度限制优化（标题通常不超过60字符）
- 句末标点检测（带逗号、句号的长句通常不是标题）

### 3. 自动字数统计与分割
- 自动统计每个TXT文件的字数
- 根据字数自动决定是否需要分割：
  - **低于10万字**：保持完整，不分割
  - **10-20万字**：平均分成2份
  - **20-30万字**：平均分成3份
  - **30-40万字**：平均分成4份
  - 以此类推（每10万字增加一份）

### 4. 智能分割规则
- 严格按照章节边界分割
- 如果章节数能被分割份数整除，平均分配
- 如果不能整除，前面的份数可以多放一个章节
- 分割后的文件命名格式：`原文件名_part01.txt`、`原文件名_part02.txt` 等

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### GUI界面（推荐）

启动图形界面：

```bash
python gui.py
```

GUI功能说明：
- **选择文件**：点击"选择文件"按钮，可以选择多个EPUB文件
- **选择输出目录**：点击"选择目录"按钮，选择TXT文件的输出位置
- **记住默认目录**：勾选后，下次启动时会自动使用上次选择的目录
- **转换日志**：实时显示转换进度和结果，包括：
  - 原文件 → 生成文件的对应关系（用箭头连接）
  - 每个文件的字数统计
  - **百分比显示**（重点高亮，红色加粗）
  - 转换成功/失败状态

### 命令行界面

```bash
# 转换当前目录下的所有EPUB文件
python main.py

# 转换指定目录下的所有EPUB文件
python main.py -d /path/to/epub/files

# 转换指定的EPUB文件
python main.py -f file1.epub file2.epub

# 指定输出目录
python main.py -d /path/to/epub/files -o /path/to/output

# 只转换，不分割（禁用自动分割功能）
python main.py --no-split
```

### 命令行参数

- `-d, --directory`: 指定包含EPUB文件的目录路径
- `-f, --files`: 指定要转换的EPUB文件路径（可指定多个）
- `-o, --output`: 指定输出目录路径（默认为输入文件所在目录）
- `--no-split`: 禁用自动分割功能，只进行转换

### 使用示例

```bash
# 示例1: 转换当前目录下的所有EPUB文件
python main.py

# 示例2: 转换指定目录下的文件，并输出到另一个目录
python main.py -d ~/Downloads/epub_books -o ~/Documents/txt_books

# 示例3: 转换指定的几个文件
python main.py -f book1.epub book2.epub book3.epub

# 示例4: 只转换不分割
python main.py -d ~/Downloads/epub_books --no-split
```

## 项目结构

```
epub_to_txt/
├── main.py                 # 命令行主程序入口
├── gui.py                  # GUI图形界面程序
├── epub_parser.py         # EPUB解析模块
├── chapter_detector.py    # 章节识别规则库
├── text_splitter.py       # 文本分割模块
├── requirements.txt       # 依赖包列表
├── epub_converter_config.json  # GUI配置文件（自动生成）
└── README.md             # 项目说明文档
```

## 模块说明

### chapter_detector.py
章节识别模块，包含大量正则表达式规则，用于识别各种章节格式。

### epub_parser.py
EPUB文件解析模块，负责：
- 读取EPUB文件
- 提取文本内容
- 识别章节结构
- 转换为TXT格式

### text_splitter.py
文本分割模块，负责：
- 统计文本字数
- 计算分割份数
- 按章节分割文件

### main.py
主程序，提供命令行接口，协调各个模块完成批量转换任务。

## 注意事项

1. 确保EPUB文件格式正确，某些损坏的EPUB文件可能无法正常解析
2. 章节识别基于正则表达式，对于特殊格式可能无法识别，可以手动调整规则
3. 分割功能会删除原始转换后的TXT文件，只保留分割后的文件
4. 输出文件使用UTF-8编码

## 扩展开发

如果需要添加新的章节识别规则，可以修改 `chapter_detector.py` 中的 `_build_patterns()` 方法，添加新的正则表达式模式。

## 许可证

本项目仅供学习和个人使用。

