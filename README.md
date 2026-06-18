# PyKnowledge

个人知识管理桌面应用 — 纯 Python + PySide6 构建，SQLite 原生存储。

## 功能特性

| 模块 | 说明 |
|---|---|
| **Markdown 编辑器** | 左编辑 / 右预览分屏，实时 HTML 渲染，300ms 防抖刷新 |
| **语法高亮** | 17 条单行规则 + 多行围栏代码块 / 数学块，Catppuccin Mocha 配色 |
| **块级存储** | 段落级 Block Tree 存入 SQLite，内容可寻址 SHA256 块 ID |
| **多级标签** | 层级标签树，QTreeView 展示，支持 `/` 路径创建 |
| **FTS5 全文搜索** | 自然语言查询，`tag:` / `title:` 前缀过滤，带 `<mark>` 高亮摘要 |
| **版本历史** | Ctrl+S 手动快照，SHA256 去重，侧边双栏 Diff 对比（Myers 算法） |
| **双向链接** | `[[wikilinks]]` 自动解析 + 反向链接面板，`((block-refs))` 块级引用 |
| **导入 / 导出** | Obsidian Vault 导入（YAML frontmatter + 标签），Markdown 文件夹导出 |
| **思维导图** | 标题层级 → OPML 大纲树 + JSON（D3.js 可用） |
| **截图标注** | 区域截图 → 矩形 / 箭头 / 文字标注 → 插入笔记 |
| **附件管理** | 文件导入、拖放、右键菜单（插入 / 取消链接 / 删除） |
| **主题切换** | 暗色 / 亮色双主题，Ctrl+Shift+T 切换，CSS 自定义属性驱动 |

## 快速开始

### 环境要求

- Python ≥ 3.10
- PySide6（Qt for Python）

### 安装与运行

```bash
# 克隆仓库
git clone https://github.com/WEN454545/Py_Project.git
cd Py_Project

# 安装依赖
pip install -e ".[dev]"

# 启动应用
python -m py_project.main

# 或使用注册的命令行入口
py-knowledge
```

### 运行测试

```bash
# 全部测试
pytest tests/ -v

# 单文件测试
pytest tests/test_database.py -v

# 独立验证脚本（119 项断言，无需 pytest）
python tests/test_verify_all.py
```

## 项目结构

```
Py_Project/
├── pyproject.toml                      # 项目元数据、依赖、入口、pytest 配置
├── README.md                           # 本文件
│
├── py_project/                         # 主包
│   ├── __init__.py
│   ├── main.py                         # 入口：调用 ui.app.run()
│   ├── config.py                       # 平台路径、编辑器/窗口/搜索等配置常量
│   │
│   ├── core/                           # 领域模型（零依赖，纯 dataclass）
│   │   ├── note.py                     # Note, Block, BlockType 枚举
│   │   ├── tag.py                      # Tag（parent_tag_id 层级）
│   │   ├── link.py                     # Link（有向边）, LinkType 枚举
│   │   ├── attachment.py               # Attachment, AttachmentType 枚举
│   │   ├── version.py                  # Version（全文本快照）
│   │   └── search_result.py            # SearchResult（含高亮片段）
│   │
│   ├── storage/                        # SQLite 持久层
│   │   ├── database.py                 # 连接管理、SCHEMA_SQL（9 表 + FTS5）、迁移
│   │   ├── note_repo.py                # 笔记与 Block 的增删改查
│   │   ├── tag_repo.py                 # 层级标签操作 + 笔记关联
│   │   ├── link_repo.py                # 双向链接存取
│   │   ├── version_repo.py             # 版本保存 / 恢复 / 去重
│   │   ├── search_repo.py              # FTS5 封装：索引更新 / 搜索 / 摘要
│   │   └── attachment_repo.py          # 附件元数据存取
│   │
│   ├── engine/                         # 业务逻辑（只依赖 core/）
│   │   ├── markdown_parser.py          # 四阶段解析：分割 → 分类 → 嵌套 → 内联
│   │   ├── markdown_to_html.py         # Block Tree → 主题化 HTML（bleach 清洗）
│   │   ├── block_id.py                 # SHA256 内容寻址 Block ID 生成
│   │   ├── link_resolver.py            # [[wikilink]] 与 ((block-ref)) 提取解析
│   │   ├── diff_engine.py              # 段落级 Diff（哈希快速路径 + Myers）
│   │   ├── fts_engine.py              # FTS5 查询构建器（tag:/title: 前缀）
│   │   ├── import_obsidian.py          # Obsidian Vault 扫描（YAML frontmatter）
│   │   ├── export_markdown.py          # 笔记 → Markdown 文件夹（含 frontmatter）
│   │   └── export_opml.py              # 标题层级 → OPML / D3.js JSON 思维导图
│   │
│   ├── services/                       # 编排层（桥接 UI ↔ storage/engine）
│   │   ├── note_service.py             # 笔记 CRUD、解析—存储—渲染管线
│   │   ├── tag_service.py              # 标签树增删改、路径批量创建
│   │   ├── search_service.py           # 搜索执行 + 索引重建
│   │   ├── version_service.py          # 快照 / Diff / 恢复 / 清理
│   │   ├── attachment_service.py       # 文件导入、元数据、取消链接
│   │   ├── import_export_service.py    # 导入预览 + 执行 / 批量导出
│   │   └── screenshot_service.py       # 全屏 / 区域截图、标注合成（懒加载 Qt）
│   │
│   ├── ui/                             # PySide6 表现层
│   │   ├── app.py                      # QApplication 启动、HighDPI、主窗口
│   │   ├── main_window.py              # QMainWindow：菜单栏（30 项全接线）、分割器、
│   │   │                               #   6 个 QDockWidget、主题切换（Ctrl+Shift+T）
│   │   ├── editor/
│   │   │   ├── editor_widget.py        # QPlainTextEdit + 行号栏 + 300ms 防抖
│   │   │   └── syntax_highlighter.py   # QSyntaxHighlighter（17 正则 + 2 多行规则）
│   │   ├── preview/
│   │   │   ├── preview_widget.py       # QWebEngineView HTML 实时预览
│   │   │   └── preview_styles.py       # 暗 / 亮主题调色板 + CSS 生成（自定义属性）
│   │   ├── panels/                     # 可停靠侧边面板
│   │   │   ├── note_list_panel.py      # 笔记列表，点击加载
│   │   │   ├── tag_panel.py            # 层级标签树（QTreeView）
│   │   │   ├── tag_model.py            # QAbstractItemModel 标签数据模型
│   │   │   ├── search_panel.py         # FTS5 搜索框 + 结果列表
│   │   │   ├── backlinks_panel.py      # 反向链接列表（引用当前笔记的笔记）
│   │   │   ├── version_panel.py        # 版本列表 + 对比 / 恢复按钮
│   │   │   └── attachment_panel.py     # 附件列表 + 右键菜单
│   │   ├── dialogs/                    # 模态对话框
│   │   │   ├── version_diff_dialog.py  # 双栏版本对比（QTextBrowser）
│   │   │   ├── import_dialog.py        # Obsidian 导入向导（扫描 → 预览 → 导入）
│   │   │   ├── export_dialog.py        # Markdown 导出选项（目录、扁平 / 树形）
│   │   │   ├── tag_editor_dialog.py    # 标签名称 / 父标签编辑
│   │   │   └── screenshot_dialog.py    # 区域选择 + 标注叠加层（矩形/箭头/文字）
│   │   └── widgets/                    # 可复用小型控件
│   │       └── __init__.py
│   │
│   ├── utils/                          # 工具函数
│   │   ├── hash_utils.py              # sha256(), short_hash()
│   │   ├── file_utils.py              # safe_filename(), ensure_dir()
│   │   └── time_utils.py              # now_iso(), format_relative(), format_full()
│   │
│   └── resources/                      # 图标、主题、默认模板
│
└── tests/                              # 测试套件（in-memory SQLite）
    ├── conftest.py                     # pytest fixtures（temp_db_path, in_memory_db）
    ├── test_database.py                # Phase 0：Schema、Model、CRUD、Utils（14 项）
    ├── test_phase2.py                  # 标签 / 版本 / 搜索 / Diff / 链接 / 导入导出（19 项）
    ├── test_phase4.py                  # OPML / 思维导图 JSON / 主题 CSS / 主题化 HTML
    └── test_verify_all.py             # 独立综合验证脚本（119 项断言，四阶段全覆盖）
```

## 架构

### 分层依赖

```
core/  ←  storage/  ←  engine/  ←  services/  ←  ui/
```

- **`core/`** — 纯 dataclass，零包内导入
- **`storage/`** — 只依赖 `core/`，直接操作 SQLite
- **`engine/`** — 只依赖 `core/`，纯业务逻辑，无副作用
- **`services/`** — 编排 storage 与 engine，向 UI 暴露统一接口
- **`ui/`** — 只通过 services 访问数据，不直接触 storage/engine

### 数据库

9 张表 + 1 个 FTS5 虚拟表：

| 表 | 用途 |
|---|---|
| `notes` | 笔记元数据（UUID、标题、软删除） |
| `blocks` | 段落级内容树（parent_block_id 自引用） |
| `tags` | 层级标签（parent_tag_id 自引用） |
| `note_tags` | 笔记—标签多对多 |
| `links` | 有向链接（wikilink / block_ref / url） |
| `block_references` | 块级引用精确记录 |
| `versions` | Ctrl+S 全文本快照（content_hash 去重） |
| `attachments` | 附件元数据（文件路径、MIME、尺寸、标注 JSON） |
| `schema_version` | 迁移版本追踪 |
| `notes_fts` | FTS5 虚拟表（title, body, tags） |

### Block 解析管线

```
原始文本 → 空行分割 → 块类型分类 → 树形嵌套 → 内联解析 → HTML 渲染
```

- Block ID = `SHA256(note_id + ":" + block_order + ":" + content_raw)[:12]`（内容可寻址）
- 支持类型：标题、段落、代码块、数学块、表格、列表、引用块、分隔线

### 信号 / 槽核心链路

```
EditorWidget.textChanged()
  → debounce 300ms → NoteService.on_text_changed()
  → parse_markdown() → link_resolver.resolve_all()
  → note_repo.save_blocks() → search_repo.update_fts()
  → render_blocks_to_html() → PreviewWidget.setHtml()
```

## 快捷键

| 快捷键 | 功能 |
|---|---|
| `Ctrl+S` | 保存 + 版本快照 + FTS 索引更新 + 链接解析 |
| `Ctrl+Shift+T` | 暗色 / 亮色主题切换 |
| `Ctrl+N` | 新建笔记 |
| `Ctrl+F` | 搜索面板 |
| `Ctrl+Z` / `Ctrl+Y` | 撤销 / 重做 |
| `Ctrl+B` / `Ctrl+I` | 粗体 / 斜体 |

## 开发阶段

| 阶段 | 内容 |
|---|---|
| **Phase 0** | 项目脚手架、6 个核心模型、9 表 + FTS5 Schema、工具函数 |
| **Phase 1** | 分屏编辑器 + 实时预览、4 阶段 Markdown 解析、HTML 渲染 |
| **Phase 2** | 多级标签树、FTS5 搜索、版本历史 + Diff、双向链接、Obsidian 导入 / Markdown 导出 |
| **Phase 3** | 语法高亮、截图标注、附件管理、30 个菜单项全接线 |
| **Phase 4** | 思维导图 → OPML/JSON、暗/亮双主题、解析器修复 |

## 技术栈

| 组件 | 库 |
|---|---|
| GUI | PySide6 ≥ 6.6 |
| Markdown 解析 | markdown-it-py + mdit-py-plugins |
| 代码高亮 | Pygments |
| 截图 / 图片 | Pillow |
| 版本 Diff | diff-match-patch |
| OPML 导出 | lxml |
| HTML 清洗 | bleach |
| YAML 解析 | PyYAML |
| 文件名生成 | python-slugify |
| 测试 | pytest + pytest-qt |

## 许可证

MIT
