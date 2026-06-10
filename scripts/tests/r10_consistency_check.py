# -*- coding: utf-8 -*-
"""
r10_consistency_check.py · R10 文案-行为对账扫描(V4-0.2)

V3.0.2 的 doc-code-consistency 扫描只覆盖 "print 文案 vs 控制流", 是
人工扫的。V4-0 audit §5 发现该扫描漏了 business_model 引用一片
(16+2 处空指针)。本脚本机械扫三类引用违规:

  (b) 注释/文档里的文件路径引用 (示例形态: <topdir>/<file>.md /
      <topdir>/<file>.py / <topdir>/<sub>/)
  (c) 字面引用的常量 (module.CONSTANT_NAME)
  (d) business_model §X #NXX 锚点引用 (验证业务模型文档含对应锚点)

不在 v1 覆盖范围:
  (a) print 文案 vs 控制流 — 语义检查, 留人工对账 / V5 再机械化
  (e) 字段引用 (字段 X / schema.X) — 模式太散, 误报高 / V5 再做

allow-list: scripts/tests/r10_allowlist.yaml
  - 占位路径 (如 templates/{类别}/ 中带 {}) 跳过
  - 跨仓引用 (如 ../handbook/) 跳过
  - 已知合法的虚指
  - SKILL.md / README 同文件自指允许

用法:
    ./run_script.bat tests/r10_consistency_check.py
    ./run_script.bat tests/r10_consistency_check.py --root <dir>
    ./run_script.bat tests/r10_consistency_check.py --report <path>
    ./run_script.bat tests/r10_consistency_check.py --quiet

退出码:
    0 = 0 违规
    1 = ≥1 违规
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterator

try:
    import yaml
except ImportError:
    print("[错误] 缺少 PyYAML 依赖。", file=sys.stderr)
    sys.exit(1)


# ─────────────────────────────────────────────────────────
# 配置
# ─────────────────────────────────────────────────────────

EXCLUDE_DIRS = {'.git', '.venv', '__pycache__', 'node_modules', '.idea', '.vscode'}
SCAN_EXTENSIONS = {'.py', '.md', '.yaml', '.yml'}
# 排除特定文件 (扫描脚本自身产物 — 报告文件每次重写, 内含所有违规字面会触发
# 元递归: 上一轮报告里列的违规字面被这一轮扫到, 计数爆炸)
EXCLUDE_FILENAMES = {'_r10_report.md'}
# 排除路径前缀 (fixture 目录是测试材料 self-contained mini-repos, 由各 test_*.py
# 用 --root <fixture_dir> 单独扫, 不参与全仓扫)
EXCLUDE_PATH_PREFIXES = ('scripts/tests/fixtures/',)

# 文件路径引用模式: 以仓内顶层目录开头的相对路径
# 目录白名单基于仓内实际顶层结构, 避免误命中 (如 src/foo.py)
# v2 (V4-0.2 commit 6b): 字符类含 * ? 让 glob 占位完整匹配, 由
# _is_meta_variable_path() 后置判别
PATH_ROOT_DIRS = ('docs', 'scripts', 'templates', 'references', 'projects',
                  'plans', 'assets')
FILE_PATH_REGEX = re.compile(
    r'(?<![\w/.])'                                          # 左边界: 非字母数字/或路径分隔
    r'(?:' + '|'.join(PATH_ROOT_DIRS) + r')/'                # 顶层目录
    r'[\w./{}\-*?<>]*'                                      # 路径主体 (含占位 {} <> / glob *?)
    r'(?:\.(?:md|py|yaml|yml|csv|docx|json|txt))?'          # 可选文件后缀
    r'/?'                                                    # 可选末尾 /
)


def _is_meta_variable_path(ref: str) -> bool:
    """识别元变量占位路径 (v2 新增, V4-0.2 commit 6b):

    - glob 通配 (*, ?)
    - 大括号占位 {...} (e.g. {项目名})
    - 尖括号占位 <...> (e.g. <项目>)
    - 单大写字母占位 -N / -X / -Y / -Z (e.g. plans/v4-N.md, docs/v4-X)
    - 已知英文占位词 (your_project)

    命中即认为是规范性占位, 不视为对真实路径的引用, 跳过.
    """
    if '*' in ref or '?' in ref:
        return True
    if '{' in ref or '}' in ref:
        return True
    if '<' in ref or '>' in ref:
        return True
    # 单大写字母占位: 紧跟 - 或 / 之后的单个大写字母, 后接 . / - / / 或末尾
    if re.search(r'[/\-][A-Z](?=\.|/|\-|$)', ref):
        return True
    if 'your_project' in ref:
        return True
    return False

# module.CONSTANT 模式: 小写下划线模块名 . 全大写常量名
CONST_REF_REGEX = re.compile(
    r'\b([a-z_][a-z0-9_]*)\.([A-Z][A-Z0-9_]{2,})\b'
)

# business_model §X[.Y] #NXX 模式
BUSINESS_MODEL_REGEX = re.compile(
    r'business_model\s*'
    r'(?:§\s*(\d+(?:\.\d+)?)\s*)?'                          # 可选 §X 或 §X.Y
    r'#N(\d+)'                                              # 必须 #NXX
)

# business_model §X (无 #NXX) 模式 — 仅章节引用
BUSINESS_MODEL_SECTION_REGEX = re.compile(
    r'business_model\s*§\s*(\d+(?:\.\d+)?)\b'
)

# 注释/字符串模式 (用于 .py 文件抽取被扫文本)
# 简单做法: 把整个 .py 当文本扫, 因为正则模式本身就够特异 (FILE_PATH_REGEX 命中
# 必须以 PATH_ROOT_DIRS/ 开头, CONST_REF_REGEX 必须 module.UPPER) — 即使命中
# 代码而非注释也通常是合法引用 (e.g. 实际 import)
# 如未来误报多, 再加 ast 抽取 docstring/comment


# ─────────────────────────────────────────────────────────
# allow-list
# ─────────────────────────────────────────────────────────

DEFAULT_ALLOWLIST: dict = {
    'paths': [],
    'constants': [],
    'business_model_anchors': [],
    'self_ref_files': [],
}


def load_allowlist(path: Path) -> dict:
    if not path.exists():
        return DEFAULT_ALLOWLIST.copy()
    data = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    merged = DEFAULT_ALLOWLIST.copy()
    for k, v in data.items():
        if isinstance(v, list):
            merged[k] = v
    return merged


def _matches_allow_pattern(value: str, patterns: list) -> bool:
    """value 匹配 allowlist 任一 pattern (支持 * 通配)."""
    for pat in patterns:
        if not isinstance(pat, str):
            continue
        # 把简单通配转 regex
        rx = re.escape(pat).replace(r'\*', r'.*')
        if re.fullmatch(rx, value):
            return True
    return False


# ─────────────────────────────────────────────────────────
# 索引: 仓内有哪些常量定义 / business_model 锚点
# ─────────────────────────────────────────────────────────

CONST_DEF_REGEX = re.compile(r'^([A-Z][A-Z0-9_]{2,})\s*[:=]')  # 顶层常量定义
ANCHOR_REGEX = re.compile(r'^###?\s+§?\s*(\d+(?:\.\d+)?)\s*(?:#N(\d+))?')


def index_constants(root: Path) -> dict[str, set[str]]:
    """扫 scripts/*.py, 返回 {module_name: set(CONSTANT_NAME)}."""
    index: dict[str, set[str]] = {}
    scripts_dir = root / 'scripts'
    if not scripts_dir.exists():
        return index
    for py in scripts_dir.rglob('*.py'):
        if any(part in EXCLUDE_DIRS for part in py.parts):
            continue
        module = py.stem
        consts: set[str] = set()
        try:
            for line in py.read_text(encoding='utf-8').splitlines():
                m = CONST_DEF_REGEX.match(line)
                if m:
                    consts.add(m.group(1))
        except (OSError, UnicodeDecodeError):
            continue
        if consts:
            index[module] = consts
    return index


def index_business_model_anchors(root: Path) -> tuple[set[tuple[str, str]], set[str]]:
    """扫业务模型文档 (docs 目录下 business_model 开头的 md), 返回
    (含 #N 编号的锚点集, 仅章节编号集)."""
    anchors_with_n: set[tuple[str, str]] = set()
    sections_only: set[str] = set()
    docs_dir = root / 'docs'
    if not docs_dir.exists():
        return anchors_with_n, sections_only
    for md in docs_dir.glob('business_model*.md'):
        try:
            for line in md.read_text(encoding='utf-8').splitlines():
                m = ANCHOR_REGEX.match(line)
                if m:
                    section = m.group(1)
                    n_num = m.group(2)
                    if n_num:
                        anchors_with_n.add((section, n_num))
                    sections_only.add(section)
        except (OSError, UnicodeDecodeError):
            continue
    return anchors_with_n, sections_only


# ─────────────────────────────────────────────────────────
# 扫描主循环
# ─────────────────────────────────────────────────────────


def iter_scan_files(root: Path) -> Iterator[Path]:
    for p in root.rglob('*'):
        if not p.is_file():
            continue
        if any(part in EXCLUDE_DIRS for part in p.parts):
            continue
        if p.name in EXCLUDE_FILENAMES:
            continue
        if p.suffix not in SCAN_EXTENSIONS:
            continue
        rel = p.relative_to(root).as_posix()
        if any(rel.startswith(prefix) for prefix in EXCLUDE_PATH_PREFIXES):
            continue
        yield p


def scan_file(
    file_path: Path,
    root: Path,
    const_index: dict[str, set[str]],
    bm_anchors_with_n: set[tuple[str, str]],
    bm_sections: set[str],
    allowlist: dict,
) -> list[dict]:
    """单文件扫, 返回违规列表."""
    violations: list[dict] = []
    rel_path = file_path.relative_to(root)
    rel_str = str(rel_path).replace('\\', '/')

    try:
        text = file_path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return violations

    # 同文件自指允许 (e.g. SKILL.md 引 SKILL.md, README 引 README)
    same_file_allowed = rel_str in allowlist.get('self_ref_files', []) or \
        file_path.name in allowlist.get('self_ref_files', [])

    lines = text.splitlines()
    for lineno, line in enumerate(lines, start=1):
        # (b) 文件路径引用
        for m in FILE_PATH_REGEX.finditer(line):
            ref = m.group(0).rstrip('.,;:!?。,;:!?')
            # 自指
            if same_file_allowed and (ref == rel_str or ref.endswith('/' + file_path.name)):
                continue
            # 元变量占位 (glob / 大括号 / 尖括号 / 单大写字母 / your_project)
            if _is_meta_variable_path(ref):
                continue
            # allow-list
            if _matches_allow_pattern(ref, allowlist.get('paths', [])):
                continue
            # 检查路径
            target = root / ref
            if not target.exists():
                violations.append({
                    'file': rel_str,
                    'line': lineno,
                    'type': 'path_ref',
                    'ref': ref,
                    'reason': '路径不存在',
                    'snippet': line.strip()[:120],
                })

        # (c) 字面常量引用
        for m in CONST_REF_REGEX.finditer(line):
            module = m.group(1)
            const = m.group(2)
            full = f'{module}.{const}'
            if _matches_allow_pattern(full, allowlist.get('constants', [])):
                continue
            if module not in const_index:
                # 模块不存在 → 误命中 (e.g. random.UPPER 在 stdlib), skip
                continue
            if const not in const_index[module]:
                violations.append({
                    'file': rel_str,
                    'line': lineno,
                    'type': 'const_ref',
                    'ref': full,
                    'reason': f'{module}.py 中未定义此常量',
                    'snippet': line.strip()[:120],
                })

        # (d) business_model §X #NXX
        for m in BUSINESS_MODEL_REGEX.finditer(line):
            section = m.group(1) or ''
            n_num = m.group(2)
            anchor_label = f'business_model §{section} #N{n_num}' if section \
                else f'business_model #N{n_num}'
            if _matches_allow_pattern(anchor_label,
                                       allowlist.get('business_model_anchors', [])):
                continue
            if not bm_anchors_with_n:
                violations.append({
                    'file': rel_str,
                    'line': lineno,
                    'type': 'business_model_anchor',
                    'ref': anchor_label,
                    'reason': '业务模型文档不存在 / 无锚点索引',
                    'snippet': line.strip()[:120],
                })
                continue
            if section and (section, n_num) not in bm_anchors_with_n:
                violations.append({
                    'file': rel_str,
                    'line': lineno,
                    'type': 'business_model_anchor',
                    'ref': anchor_label,
                    'reason': f'business_model 文档无 §{section} #N{n_num} 锚点',
                    'snippet': line.strip()[:120],
                })
            elif not section:
                # 无 §X 只给 #NXX, 校验 #NXX 在任一 section 下存在
                if not any(n == n_num for _, n in bm_anchors_with_n):
                    violations.append({
                        'file': rel_str,
                        'line': lineno,
                        'type': 'business_model_anchor',
                        'ref': anchor_label,
                        'reason': f'business_model 文档无 #N{n_num} 锚点',
                        'snippet': line.strip()[:120],
                    })

        # (d') business_model §X (无 #NXX)
        for m in BUSINESS_MODEL_SECTION_REGEX.finditer(line):
            # 跳过已被 BUSINESS_MODEL_REGEX 覆盖的位置
            if BUSINESS_MODEL_REGEX.search(line[m.start():m.end() + 30]):
                continue
            section = m.group(1)
            anchor_label = f'business_model §{section}'
            if _matches_allow_pattern(anchor_label,
                                       allowlist.get('business_model_anchors', [])):
                continue
            if not bm_sections:
                violations.append({
                    'file': rel_str,
                    'line': lineno,
                    'type': 'business_model_section',
                    'ref': anchor_label,
                    'reason': '业务模型文档不存在 / 无章节索引',
                    'snippet': line.strip()[:120],
                })
                continue
            if section not in bm_sections:
                violations.append({
                    'file': rel_str,
                    'line': lineno,
                    'type': 'business_model_section',
                    'ref': anchor_label,
                    'reason': f'business_model 文档无 §{section} 章节',
                    'snippet': line.strip()[:120],
                })

    return violations


# ─────────────────────────────────────────────────────────
# 报告渲染
# ─────────────────────────────────────────────────────────


V1_V2_PRECISION_LESSON = """
---

## 扫描精度演化记录 (v1 → v2)

V4-0.2 commit 6 期间, 扫描脚本经历了一次精度调整:

- **v1 全仓扫**: 66 处违规
- **实际**: **1 真违规** (b_mode_extract.py:105 引用已删常量 `B_MODE_EXTRACT_PROMPT`) + **65 误报**
- **v2 (commit 6b)**: 加元变量识别 (`*` / `?` / `-N` / `-X` / `your_project` / `{}` / `<>`)
  + EXCLUDE_PATH_PREFIXES (fixture 目录不参与全仓扫) + allowlist 扩 (历史/未来引用 / 测试材料 / 历史佐证常量),
  归 **0**.

**教训**: 扫描类工具的 fixture **不能只验"抓得全真违规"**, 还要验"不误抓合法样本"
(元变量占位 / 跨仓引用 / 合法 glob). 这是 fixture-first clean+dirty 配对的一个盲区维度 —
clean fixture 必须包含"看起来像违规但其实合法"的样本, 才能在脚本规则收紧/放宽时
立刻暴露误报率退化. (clean/scripts/legitimate_lookalikes.py + case_8 即此用途.)
"""


def render_report(violations: list[dict], root: Path) -> str:
    lines = ['# R10 一致性扫描报告', '']
    lines.append(f'扫描根: `{root}`')
    lines.append(f'违规总数: **{len(violations)}**')
    lines.append('')
    if not violations:
        lines.append('[OK] 无违规。')
        lines.append(V1_V2_PRECISION_LESSON)
        return '\n'.join(lines) + '\n'

    by_type: dict[str, list[dict]] = {}
    for v in violations:
        by_type.setdefault(v['type'], []).append(v)

    for vtype in sorted(by_type.keys()):
        vs = by_type[vtype]
        lines.append(f'## {vtype} ({len(vs)} 处)')
        lines.append('')
        lines.append('| 文件 | 行 | 引用 | 失败原因 | 上下文 |')
        lines.append('|---|---|---|---|---|')
        for v in vs:
            snippet = v['snippet'].replace('|', '\\|')
            lines.append(
                f"| {v['file']} | {v['line']} | `{v['ref']}` | {v['reason']} | "
                f"{snippet} |"
            )
        lines.append('')
    return '\n'.join(lines) + '\n'


# ─────────────────────────────────────────────────────────
# 主入口
# ─────────────────────────────────────────────────────────


def run_scan(root: Path, allowlist_path: Path | None = None) -> tuple[list[dict], str]:
    """跑扫描, 返回 (violations, rendered_report)."""
    allowlist = load_allowlist(allowlist_path) if allowlist_path else \
        DEFAULT_ALLOWLIST.copy()
    const_index = index_constants(root)
    bm_anchors_with_n, bm_sections = index_business_model_anchors(root)

    violations: list[dict] = []
    for fp in iter_scan_files(root):
        violations.extend(scan_file(
            fp, root, const_index, bm_anchors_with_n, bm_sections, allowlist
        ))

    report = render_report(violations, root)
    return violations, report


def main() -> int:
    parser = argparse.ArgumentParser(description='R10 一致性扫描')
    parser.add_argument('--root', type=Path, default=None,
                        help='扫描根目录, 默认仓库根')
    parser.add_argument('--report', type=Path, default=None,
                        help='报告 md 输出路径, 默认在 scripts/tests/ 下名 _r10_report.md')
    parser.add_argument('--allowlist', type=Path, default=None,
                        help='allowlist yaml 路径, 默认 scripts/tests/r10_allowlist.yaml')
    parser.add_argument('--quiet', action='store_true', help='只输出汇总, 不打印违规明细')
    args = parser.parse_args()

    if args.root is None:
        args.root = Path(__file__).resolve().parent.parent.parent
    if args.report is None:
        args.report = Path(__file__).resolve().parent / '_r10_report.md'
    if args.allowlist is None:
        args.allowlist = Path(__file__).resolve().parent / 'r10_allowlist.yaml'

    args.root = args.root.resolve()
    print(f'[信息] 扫描根: {args.root}')
    print(f'[信息] allowlist: {args.allowlist}'
          f'{" (不存在, 走默认)" if not args.allowlist.exists() else ""}')
    print()

    violations, report = run_scan(args.root, args.allowlist)

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding='utf-8')
    print(f'[信息] 报告写入: {args.report}')
    print()

    if not violations:
        print('[OK] R10 扫描通过: 0 违规。')
        return 0

    print(f'[FAIL] R10 扫描发现 {len(violations)} 处违规:')
    by_type: dict[str, int] = {}
    for v in violations:
        by_type[v['type']] = by_type.get(v['type'], 0) + 1
    for t, c in sorted(by_type.items()):
        print(f'    - {t}: {c}')

    if not args.quiet:
        print()
        print('明细:')
        for v in violations:
            print(f"  [{v['type']}] {v['file']}:{v['line']}  {v['ref']}  -- {v['reason']}")

    return 1


if __name__ == '__main__':
    sys.exit(main())
