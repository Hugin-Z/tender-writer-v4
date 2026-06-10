#!/usr/bin/env python3
"""
build_baseline.py — A 模式基线快照生成工具

读取当前 A 模式产出文件,计算 hash 和合规指标,
生成 a_mode_baseline.json 并追加 changelog 记录。

用法:
  python scripts/build_baseline.py \
    --project demo_cadre_training \
    --mode A \
    --reason "初始基线冻结"
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta

# 项目根目录 = 脚本所在目录的上一级
ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))

# 工具链文件清单(相对 ROOT),用于计算 toolchain_fingerprint
# v2 封板(2026-04-22)扩容:
#   新增规则层 CLAUDE.md / ai_output_rules.md / 5 类 outline 模板
#   新增脚本 c_mode_run / b_mode_run / check_cross_consistency / c_mode_docx_passthrough
#   将 v45_merge / export_deliverables / c_mode_* / b_mode_* 纳入追踪
TOOLCHAIN_FILES = [
    # 规则层(v2 新增)
    'CLAUDE.md',
    'references/ai_output_rules.md',
    # 流程/模型文档(v2 蒸馏后保留的核心)
    'SKILL.md',
    'references/doc_format_spec.md',
    # outline 类型化模板(v2 新增,5 类 × 2 文件)
    'references/outline_templates/README.md',
    'references/outline_templates/engineering/outline_skeleton.md',
    'references/outline_templates/engineering/guidance.md',
    'references/outline_templates/platform/outline_skeleton.md',
    'references/outline_templates/platform/guidance.md',
    'references/outline_templates/research/outline_skeleton.md',
    'references/outline_templates/research/guidance.md',
    'references/outline_templates/planning/outline_skeleton.md',
    'references/outline_templates/planning/guidance.md',
    'references/outline_templates/other/outline_skeleton.md',
    'references/outline_templates/other/guidance.md',
    # 脚本(原有)
    'scripts/parse_tender.py',
    'scripts/build_scoring_matrix.py',
    'scripts/generate_outline.py',
    'scripts/docx_builder.py',
    'scripts/append_chapter.py',
    'scripts/check_chapter.py',
    'scripts/compliance_check.py',
    'scripts/count_words.py',
    'scripts/update_score_positions.py',
    'scripts/brief_schema.py',
    'scripts/migrate_brief_schema.py',
    # 脚本(v2 新增或大改)
    'scripts/c_mode_extract.py',
    'scripts/c_mode_fill.py',
    'scripts/c_mode_run.py',
    'scripts/b_mode_extract.py',
    'scripts/b_mode_fill.py',
    'scripts/b_mode_run.py',
    'scripts/v45_merge.py',
    'scripts/export_deliverables.py',
    'scripts/check_cross_consistency.py',
    'scripts/c_mode_docx_passthrough.py',
    # v2 补丁 1:投标主体选择(回补)
    'scripts/select_bidding_entity.py',
]

# baseline 追踪的产出物清单(key = json 中的字段名, value = 相对 output 目录)
# 早期命名为 TRACKED_OUTPUTS,现已扩展到 C 模式产出,故重命名为 TRACKED_OUTPUTS。
TRACKED_OUTPUTS = {
    'tender_brief.json': 'tender_brief.json',
    'tender_brief.reviewed': 'tender_brief.reviewed',  # V52+V53 review 标记
    'scoring_matrix.csv': 'scoring_matrix.csv',
    'outline.md': 'outline.md',
    'tender_response.docx': 'tender_response.docx',
    'chapters/part_08/chapter_03_对项目理解.md': 'chapters/part_08/chapter_03_对项目理解.md',
    'chapters/part_08/chapter_04_技术服务.md': 'chapters/part_08/chapter_04_技术服务.md',
    'chapters/part_08/chapter_05_质量保证措施.md': 'chapters/part_08/chapter_05_质量保证措施.md',
    'chapters/part_08/chapter_06_售后方案.md': 'chapters/part_08/chapter_06_售后方案.md',
    # C 模式产出(V48 切片验证首次纳入)
    'c_mode/响 应 函/template.docx': 'c_mode/响 应 函/template.docx',
    'c_mode/响 应 函/variables.yaml': 'c_mode/响 应 函/variables.yaml',
    'c_mode/响 应 函/filled.docx': 'c_mode/响 应 函/filled.docx',
    # C.2 切片(法定代表人身份证明)
    'c_mode/法定代表人身份证明/template.docx': 'c_mode/法定代表人身份证明/template.docx',
    'c_mode/法定代表人身份证明/variables.yaml': 'c_mode/法定代表人身份证明/variables.yaml',
    'c_mode/法定代表人身份证明/filled.docx': 'c_mode/法定代表人身份证明/filled.docx',
    # C.3 切片(分项报价表)
    'c_mode/分项报价表/template.docx': 'c_mode/分项报价表/template.docx',
    'c_mode/分项报价表/variables.yaml': 'c_mode/分项报价表/variables.yaml',
    'c_mode/分项报价表/filled.docx': 'c_mode/分项报价表/filled.docx',
    # C.4 切片(商务和技术偏差表,0 变量,路径 B' 最简版)
    'c_mode/商务和技术偏差表/template.docx': 'c_mode/商务和技术偏差表/template.docx',
    'c_mode/商务和技术偏差表/variables.yaml': 'c_mode/商务和技术偏差表/variables.yaml',
    'c_mode/商务和技术偏差表/filled.docx': 'c_mode/商务和技术偏差表/filled.docx',
    # C.5 切片(开标一览表,C-template 三件套)
    # V4-0.2 修正(audit §5 #2):原注释/entry 标 V60 C-reference 首例,
    # 实测 demo_cadre_training 该 Part sub_mode=C-template,产 filled.docx 而非
    # instructions.md。C-reference 首例执行端样例 V4-3 评估后决定不建
    # (demo_cadre_training 无单独提交件需求),推迟到 V4 整体完成后由真实
    # 使用场景驱动补 entry。
    'c_mode/开标一览表/template.docx': 'c_mode/开标一览表/template.docx',
    'c_mode/开标一览表/variables.yaml': 'c_mode/开标一览表/variables.yaml',
    'c_mode/开标一览表/filled.docx': 'c_mode/开标一览表/filled.docx',
    # V61 B 模式切片 part[6] 七、资格审查资料
    'b_mode/资格审查资料/manifest.yaml': 'b_mode/资格审查资料/manifest.yaml',
    'b_mode/资格审查资料/assembled.docx': 'b_mode/资格审查资料/assembled.docx',
    'b_mode/资格审查资料/.pending_marker': 'b_mode/资格审查资料/.pending_marker',
    # V61 B 模式切片 part[8] 九、其他资料
    'b_mode/其他资料/manifest.yaml': 'b_mode/其他资料/manifest.yaml',
    'b_mode/其他资料/assembled.docx': 'b_mode/其他资料/assembled.docx',
    'b_mode/其他资料/.pending_marker': 'b_mode/其他资料/.pending_marker',
}

# V62 V45 整标合并器产出:不在 output/ 下,而在 projects/{project}/final_tender_package/
# 单独字典维护,build_baseline 主流程分开 hash
FINAL_TENDER_OUTPUTS = {
    'final_tender_package/final_response.docx': 'final_tender_package/final_response.docx',
    'final_tender_package/operations_checklist.md': 'final_tender_package/operations_checklist.md',
    'final_tender_package/pending_manual_work.md': 'final_tender_package/pending_manual_work.md',
}


def sha256_file(path):
    """计算文件的 sha256 hexdigest。"""
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return f'sha256:{h.hexdigest()}'


def compute_builder_hash():
    """计算 build_baseline.py 自身 sha256,用于 baseline json 追踪建基线的工具版本。"""
    return sha256_file(__file__)


def detect_baseline_drift(baseline_dir, output_dir):
    """探测基线与磁盘的 hash 漂移。返回 diff 清单。
    FINAL_TENDER_OUTPUTS 的路径相对 project_dir(output_dir 的父目录)。"""
    baseline_path = os.path.join(baseline_dir, 'a_mode_baseline.json')
    if not os.path.isfile(baseline_path):
        return []

    with open(baseline_path, 'r', encoding='utf-8') as f:
        old_baseline = json.load(f)

    old_hashes = old_baseline.get('file_hashes', {})
    diffs = []
    project_dir = os.path.dirname(output_dir)

    for rel_path, old_hash in old_hashes.items():
        # 根据前缀判断文件在哪个根目录
        if rel_path.startswith('final_tender_package/'):
            full_path = os.path.join(project_dir, rel_path)
        else:
            full_path = os.path.join(output_dir, rel_path)
        if not os.path.isfile(full_path):
            diffs.append((rel_path, old_hash, None))
            continue
        new_hash = sha256_file(full_path)
        if new_hash != old_hash:
            diffs.append((rel_path, old_hash, new_hash))

    return diffs


def compute_toolchain_fingerprint(root):
    """计算工具链聚合指纹。返回 (fingerprint, manifest)。"""
    missing = []
    for rel in TOOLCHAIN_FILES:
        full = os.path.join(root, rel)
        if not os.path.isfile(full):
            missing.append(rel)

    if missing:
        print('错误: TOOLCHAIN_FILES 中以下文件不存在:', file=sys.stderr)
        for m in missing:
            print(f'  - {m}', file=sys.stderr)
        print('清单过时,请根据工具链真实文件名修正 scripts/build_baseline.py',
              file=sys.stderr)
        print('中的 TOOLCHAIN_FILES 常量。不允许自动跳过缺失文件,跳过会让指纹',
              file=sys.stderr)
        print('失真。', file=sys.stderr)
        sys.exit(1)

    manifest = {}
    for rel in TOOLCHAIN_FILES:
        full = os.path.join(root, rel)
        manifest[rel] = sha256_file(full)

    # 按 key 字典序排列,拼接后再取 sha256
    sorted_entries = sorted(manifest.items())
    combined = '\n'.join(f'{path}:{h}' for path, h in sorted_entries)
    fingerprint = f'sha256:{hashlib.sha256(combined.encode("utf-8")).hexdigest()}'

    return fingerprint, dict(sorted_entries)


def load_compliance_metrics(output_dir):
    """取五个合规指标。优先读 compliance_metrics.json(机器接口),
    回退到 compliance_report.md 正则解析(兼容旧版产出)。"""
    json_path = os.path.join(output_dir, 'compliance_metrics.json')
    if os.path.isfile(json_path):
        return _load_metrics_from_json(json_path)
    report_path = os.path.join(output_dir, 'compliance_report.md')
    if not os.path.isfile(report_path):
        print(f'错误: compliance_metrics.json 和 compliance_report.md 均不存在',
              file=sys.stderr)
        sys.exit(1)
    return _load_metrics_from_markdown(report_path)


def _load_metrics_from_json(json_path):
    """从 compliance_metrics.json 读取五个指标。"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    required = ['coverage_pct', 'star_explicit', 'triangle_unclear',
                 'template_residue_count', 'format_issues_count']
    missing = [k for k in required if k not in data]
    if missing:
        print(f'错误: compliance_metrics.json 缺少字段: {", ".join(missing)}',
              file=sys.stderr)
        sys.exit(1)
    return {
        'coverage_pct': float(data['coverage_pct']),
        'star_count': int(data['star_explicit']),
        'triangle_count': int(data['triangle_unclear']),
        'template_residue': int(data['template_residue_count']),
        'format_issues': int(data['format_issues_count']),
    }


def _load_metrics_from_markdown(report_path):
    """从 compliance_report.md 正则解析五个指标(回退路径)。"""
    with open(report_path, 'r', encoding='utf-8') as f:
        content = f.read()

    metrics = {}
    errors = []

    m = re.search(r'覆盖率:\s*([\d.]+)%', content)
    if m:
        metrics['coverage_pct'] = float(m.group(1))
    else:
        errors.append('coverage_pct')

    m = re.search(r'明确响应:\s*(\d+)', content)
    if m:
        metrics['star_count'] = int(m.group(1))
    else:
        errors.append('star_count')

    m = re.search(r'未明确响应:\s*(\d+)', content)
    if m:
        metrics['triangle_count'] = int(m.group(1))
    else:
        errors.append('triangle_count')

    residue_lines = re.findall(r'^- ❌ 残留.*$', content, re.MULTILINE)
    metrics['template_residue'] = len(residue_lines)

    format_section = re.search(
        r'## 四、格式检查\s*\n(.*?)(?=\n## |\n---|\Z)',
        content, re.DOTALL
    )
    if format_section:
        fmt_text = format_section.group(1)
        if '未发现明显问题' in fmt_text:
            metrics['format_issues'] = 0
        else:
            issue_lines = re.findall(r'^- (?!✅).*$', fmt_text, re.MULTILINE)
            metrics['format_issues'] = len(issue_lines)
    else:
        errors.append('format_issues')

    if errors:
        print(f'错误: compliance_report.md 以下字段解析失败: {", ".join(errors)}',
              file=sys.stderr)
        sys.exit(1)

    return metrics


def build_changelog_entry(version, reason, mode, file_hashes, metrics, ts_str,
                          fingerprint, manifest):
    """构造一条 changelog 追加记录。"""
    # hash 前 8 位摘要
    short = {}
    for key, val in file_hashes.items():
        hex_part = val.replace('sha256:', '')[:8]
        if 'chapter_03' in key:
            short['chapter_03'] = hex_part
        elif 'chapter_04' in key:
            short['chapter_04'] = hex_part
        elif 'chapter_05' in key:
            short['chapter_05'] = hex_part
        elif 'chapter_06' in key:
            short['chapter_06'] = hex_part
        else:
            short[key] = hex_part

    fp_short = fingerprint.replace('sha256:', '')[:8]

    lines = [
        f'## baseline_version = {version}',
        '',
        f'- 建立时间: {ts_str}',
        f'- 原因: {reason}',
        f'- 模式: {mode}',
        f'- 工具链指纹(前 8 位): {fp_short}',
        f'- 工具链文件数: {len(manifest)}',
    ]
    # 文件 hash 摘要:toolchain-only 时 file_hashes 为空,跳过该节
    if file_hashes:
        lines.append('- 文件 hash 摘要(前 8 位):')
        for key in ('tender_brief.json', 'scoring_matrix.csv', 'outline.md',
                    'tender_response.docx'):
            if key in short:
                lines.append(f'  - {key}: {short[key]}')
        for key in ('chapter_03', 'chapter_04', 'chapter_05', 'chapter_06'):
            if key in short:
                lines.append(f'  - {key}: {short[key]}')
    else:
        lines.append('- 文件 hash 摘要: (--toolchain-only 跳过)')
    # 合规指标:toolchain-only 时 metrics 为占位
    if metrics.get('coverage_pct') is not None:
        lines.append(
            f'- 合规指标: 覆盖率 {metrics["coverage_pct"]}%'
            f' / ★ {metrics["star_count"]}'
            f' / ▲ {metrics["triangle_count"]}'
            f' / 模板残留 {metrics["template_residue"]}'
            f' / 格式问题 {metrics["format_issues"]}'
        )
    else:
        lines.append('- 合规指标: (--toolchain-only 跳过)')
    lines.extend(['', '---', ''])
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='A 模式基线快照生成工具')
    parser.add_argument('--project', required=True, help='项目名')
    parser.add_argument('--mode', required=True, choices=['A'], help='模式(当前仅 A)')
    parser.add_argument('--reason', required=True, help='建立或更新原因')
    parser.add_argument('--no-interactive', action='store_true',
                        help='非交互模式(CI/批处理),发现漂移时仅 sleep 3 秒,不弹 y/N 询问')
    parser.add_argument('--toolchain-only', action='store_true',
                        help='v2 封板新增:只计算 toolchain_fingerprint(跳过 '
                             'TRACKED_OUTPUTS / FINAL_TENDER_OUTPUTS 的项目产物校验)。'
                             '用于"纳入追踪工具链规则+脚本"的独立场景,避免 TRACKED_OUTPUTS '
                             '对另一项目硬编码失配阻塞。')
    args = parser.parse_args()

    output_dir = os.path.join(ROOT, 'projects', args.project, 'output')
    baseline_dir = os.path.join(ROOT, 'baselines', args.project)

    # ── 步骤 0: 基线-磁盘一致性探测 ──
    drifts = detect_baseline_drift(baseline_dir, output_dir)
    if drifts:
        print(f'[warn] 发现 {len(drifts)} 个文件与上一版基线 hash 不一致:',
              file=sys.stderr)
        for rel, old, new in drifts:
            old_s = old.replace('sha256:', '')[:8] if old else 'missing'
            new_s = new.replace('sha256:', '')[:8] if new else 'missing'
            print(f'  - {rel}: {old_s} → {new_s}', file=sys.stderr)

        if args.no_interactive:
            print('这些漂移将被冻入新基线。如果其中有非预期漂移,按 Ctrl+C 中止。',
                  file=sys.stderr)
            print('等待 3 秒...', file=sys.stderr)
            time.sleep(3)
        else:
            print(f'发现 {len(drifts)} 个文件与上一版基线 hash 不一致,'
                  '这些漂移将被冻入新基线。',
                  file=sys.stderr)
            try:
                ans = input('是否继续? [y/N]: ').strip().lower()
            except EOFError:
                ans = ''
            if ans != 'y':
                print('已中止,基线未刷新。', file=sys.stderr)
                sys.exit(1)
    else:
        if os.path.isfile(os.path.join(baseline_dir, 'a_mode_baseline.json')):
            print('[info] 基线-磁盘一致性探测:所有产出物 hash 与上一版基线一致。',
                  file=sys.stderr)

    # ── 步骤 1: 读取现有基线版本 ──
    baseline_path = os.path.join(baseline_dir, 'a_mode_baseline.json')
    if os.path.exists(baseline_path):
        with open(baseline_path, 'r', encoding='utf-8') as f:
            old = json.load(f)
        version = old['baseline_version'] + 1
    else:
        version = 1

    # ── 步骤 2: 计算文件 hash ──
    # TRACKED_OUTPUTS: paths relative to output_dir
    # FINAL_TENDER_OUTPUTS: paths relative to project_dir (V62 V45 合并器产出)
    project_dir = os.path.join(ROOT, 'projects', args.project)

    file_hashes = {}
    if args.toolchain_only:
        print('[info] --toolchain-only 模式:跳过 TRACKED_OUTPUTS / '
              'FINAL_TENDER_OUTPUTS 校验,只记录 toolchain_fingerprint',
              file=sys.stderr)
    else:
        missing = []
        for rel in TRACKED_OUTPUTS.values():
            full = os.path.join(output_dir, rel)
            if not os.path.isfile(full):
                missing.append(rel)
        for rel in FINAL_TENDER_OUTPUTS.values():
            full = os.path.join(project_dir, rel)
            if not os.path.isfile(full):
                missing.append(rel)

        if missing:
            print(f'错误: 以下文件缺失,无法生成基线:', file=sys.stderr)
            for m in missing:
                print(f'  - {m}', file=sys.stderr)
            sys.exit(1)

        for key, rel in TRACKED_OUTPUTS.items():
            full = os.path.join(output_dir, rel)
            file_hashes[key] = sha256_file(full)
        for key, rel in FINAL_TENDER_OUTPUTS.items():
            full = os.path.join(project_dir, rel)
            file_hashes[key] = sha256_file(full)

    # ── 步骤 3: 取合规指标(优先 json,回退 markdown) ──
    if args.toolchain_only:
        metrics = {
            'coverage_pct': None,
            'star_count': None,
            'residual_count': None,
            'format_warn_count': None,
            'title_keyword_uncovered': None,
            '_note': '--toolchain-only 模式:跳过 compliance_metrics 采集'
        }
    else:
        metrics = load_compliance_metrics(output_dir)

    # ── 步骤 3.5: 计算工具链指纹 ──
    fingerprint, manifest = compute_toolchain_fingerprint(ROOT)

    # ── 步骤 4: 组装 json ──
    tz = timezone(timedelta(hours=8))
    now = datetime.now(tz)
    ts_str = now.strftime('%Y-%m-%dT%H:%M:%S+08:00')
    ts_human = now.strftime('%Y-%m-%d %H:%M:%S +08:00')

    baseline = {
        'project': args.project,
        'mode': args.mode,
        'baseline_version': version,
        'created_at': ts_str,
        'toolchain_fingerprint': fingerprint,
        'baseline_builder_hash': compute_builder_hash(),
        'toolchain_manifest': manifest,
        'reason': args.reason,
        'file_hashes': file_hashes,
        'compliance_metrics': metrics,
    }

    # ── 步骤 5: 写入 json ──
    os.makedirs(baseline_dir, exist_ok=True)
    with open(baseline_path, 'w', encoding='utf-8') as f:
        json.dump(baseline, f, ensure_ascii=False, indent=2)
        f.write('\n')

    # ── 步骤 6: 更新 changelog ──
    changelog_path = os.path.join(baseline_dir, 'baseline_changelog.md')
    if not os.path.exists(changelog_path):
        header = (
            f'# {args.project} A 模式基线变更日志\n'
            '\n'
            '本文件记录 a_mode_baseline.json 的每一次建立或更新。'
            '每次 build_baseline.py 执行自动追加一条记录。\n'
            '\n'
            '---\n'
            '\n'
        )
        with open(changelog_path, 'w', encoding='utf-8') as f:
            f.write(header)

    entry = build_changelog_entry(version, args.reason, args.mode,
                                  file_hashes, metrics, ts_human,
                                  fingerprint, manifest)
    with open(changelog_path, 'a', encoding='utf-8') as f:
        f.write(entry)

    # ── 打印简报 ──
    print(f'基线版本: baseline_version = {version}')
    print(f'基线文件: {baseline_path}')
    print(f'变更日志: {changelog_path}')
    print()
    fp_short = fingerprint.replace('sha256:', '')[:8]
    print(f'工具链指纹(前 8 位): {fp_short}')
    print(f'工具链文件数: {len(manifest)}')
    print()
    print('文件 hash (前 8 位):')
    for key, val in file_hashes.items():
        short_key = key.split('/')[-1] if '/' in key else key
        print(f'  {short_key}: {val.replace("sha256:", "")[:8]}')
    print()
    if args.toolchain_only:
        print('合规指标:(--toolchain-only 跳过)')
    else:
        print('合规指标:')
        print(f'  覆盖率:     {metrics["coverage_pct"]}%')
        print(f'  ★ 明确响应: {metrics["star_count"]}')
        print(f'  ▲ 未明确:   {metrics["triangle_count"]}')
        print(f'  模板残留:   {metrics["template_residue"]}')
        print(f'  格式问题:   {metrics["format_issues"]}')
    print()
    print('--- JSON 全文 ---')
    print(json.dumps(baseline, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
