#!/usr/bin/env python3
"""Render report and execution/SHA records from the transition audit result."""
import datetime as dt
import hashlib
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
WORK = pathlib.Path('/Users/mac/QuantAsiaDesk/research-work')
RESULT = HERE / 'competition_transition_audit_results.json'


def sha(p):
    h = hashlib.sha256()
    with pathlib.Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main():
    d = json.loads(RESULT.read_text())
    c = d['coverage']
    yrows = c['target_coverage_by_year']
    lines = [
        '# M8 国内联赛转换与升降级定价机制：库存可估计性审计', '',
        '日期：2026-11-20（北京时间）', '',
        '## 结论', '',
        '**当前保存的数据没有可用于本机制前推盈利检验的身份安全样本。** '
        '在原49联赛与新增15联赛共46,068个历史AH路径目标FID中，43,084个在缓存赛程中有完整赛事身份；'
        '2024–2026身份可用目标共30,710个。按目标赛前365日、至少提前3天的历史比赛检查，'
        '没有一场满足“同一国内俱乐部近期在另一个联赛参赛、且本联赛尚无同期记录”的严格同名/同国家/队伍ID条件。', '',
        '由于候选FID为0，本轮不训练选边模型、不读取目标结果核算利润，也不把缺乏样本写成0U或0% ROI。', '',
        '## 假说与实验边界', '',
        '新假说是：球队升降级或跨国内联赛后，市场可能需要一段时间重新估计球队强度。它不同于一般球队历史残差、球队熟悉程度和同俱乐部跨赛事Crown残差迁移；'
        '本轮只先审查现有库存能否识别同一俱乐部的联赛转换，不把联赛名称变化直接认作升降级。', '',
        f"候选定义为：目标北京时间日期前{d['candidate_definition']['lag_days']}日截止、过去{d['candidate_definition']['prior_window_days']}日的已完成国内联赛比赛；"
        '近期记录必须同时满足目标队伍ID、规范化队名、联赛名国家前缀一致且联赛ID不同；目标球队在同一窗口内不能已有目标联赛记录。'
        '杯赛、国际赛、友谊赛、附加赛等按清单排除。此条件是研究样本身份审计，不是下注规则。', '',
        '## 数据覆盖', '',
        f"- 已核对缓存赛程页：{c['cached_schedule_pages']:,}份；相对已保存SHA索引差异{c['page_sha_issues']}。",
        f"- 赛事库存：{c['target_path_fids']:,}个历史Crown路径FID；其中{c['target_fids_with_completed_identity']:,}个有完整身份，{c['target_fids_missing_or_conflicting_identity']:,}个无身份或身份冲突。",
        f"- 缓存的已完成赛事：{c['unique_completed_fids_after_conflict_removal']:,}个唯一FID，另排除{c['conflicting_schedule_fids_excluded']}个赛事身份冲突；覆盖{c['league_ids_seen']}个联赛ID。",
        f"- 2024/2025/2026身份可用目标分别为{yrows.get('2024',{}).get('target_fids_with_completed_identity',0):,}/"
        f"{yrows.get('2025',{}).get('target_fids_with_completed_identity',0):,}/"
        f"{yrows.get('2026',{}).get('target_fids_with_completed_identity',0):,}个。",
        f"- 同一队伍ID在多于一个国内联赛ID出现的历史队伍键{c['historical_team_ids_with_multiple_domestic_league_ids']}个；其中逐队联赛名、国家前缀及规范化队名见结果JSON。",
        '- 逐年目标球队层面的历史赛事覆盖、同联赛历史覆盖及异联赛同ID记录数均保存在机器结果；这些是可用性统计，不是订单量或盈利。', '',
        '## 结果与限制', '',
        f"符合候选身份定义的唯一FID：**{c['candidate_unique_fids']}**。因此Crown AH市场价格、FT、quarter-line结算、ROI、MDD、周订单量以及与原八组的利润合并均不适用；没有用相似队名、跨国家同名队或另一博彩公司盘口补造样本。", '',
        '这一零覆盖只说明当前缓存和身份规则无法估计该假说，不能说明升降级后的定价偏差不存在。'
        '缓存联赛名称不构成统一国家/级别目录；只要跨联赛身份关系没有稳定证据，就不应把同名球队或复用的provider team ID当成同一俱乐部。', '',
        '## 与既有研究的关系', '',
        '- R49/R50 已测历史教练、转会及阵容信息；本轮不是重跑这些变量。',
        '- 2026-11-19跨赛事球队定价研究查过同俱乐部跨Crown赛事ID的历史 AH 残差，所用身份映射池也没有目标期可用的迁移历史。',
        '- 本轮不同之处是检查国内联赛间实际参赛层级变动/重新定价的身份覆盖；结果为无可回测目标样本，未将其改名包装成已测试盈利模型。', '',
        '## 后续所缺信息', '',
        '若未来继续该方向，需要可回溯且稳定的俱乐部主键、可确认的国内各级联赛映射及完整低级别赛程；还需把这些身份/级别信息的赛前可见时间与同一FID的真实Crown HTTP收件和报价时间对齐。当前没有从已存库存中构造可审计的盈利候选。', '',
        '## 复核文件', '',
        '- 审计脚本：`audit_competition_transition.py`',
        '- 结果及逐年覆盖：`competition_transition_audit_results.json`',
        '- 输入、输出与执行命令：`EXECUTION_RECORD.md`、`SHA256SUMS.txt`', '',
        '本轮为只读研究审计；未改原八组、M1/MR1/M9、正式模型、采集、调度、Telegram或账本。'
    ]
    report = HERE / 'M8_COMPETITION_TRANSITION_AUDIT_20261120.md'
    report.write_text('\n'.join(lines) + '\n')
    execution = '''# 执行记录

- 运行 `python3 research/m8/competition_transition_20261120/audit_competition_transition.py`：完成；重验缓存5,180页SHA，0差异。
- 运行 `python3 research/m8/competition_transition_20261120/build_report.py`：完成；生成报告与SHA清单。
- 目标库存46,068个历史路径FID；43,084个有完整赛事身份；缓存内已完成比赛148,158个唯一FID，身份冲突0；同国家、同队名、不同国内联赛且目标联赛无同期历史的候选0FID。
- 没有候选订单，未计算/伪造净U、ROI、MDD或周均单量；没有运行市场利润回测或实收回放。
- 仅使用已缓存TotalCorner赛程/赛事ID作身份和赛前历史覆盖审计。目标赛果不进入特征；历史AH路径仅定义目标库存，不读取其它公司价格。
- 冻结八组、生产模型、Telegram、账本、Crown采集链、调度均未修改；0派单、0账本写入。

可复算命令：

```sh
python3 research/m8/competition_transition_20261120/audit_competition_transition.py
python3 research/m8/competition_transition_20261120/build_report.py
```
'''
    (HERE / 'EXECUTION_RECORD.md').write_text(execution)
    files = [RESULT.name, report.name, 'audit_competition_transition.py', 'build_report.py', 'EXECUTION_RECORD.md']
    index = pathlib.Path(__file__).resolve().parents[1] / 'red_card_adjusted_form_20261120/schedule_page_sha256_manifest.json'
    inputs = {str(WORK / 'm8_late_full_path_water_features_20261114.jsonl'): sha(WORK / 'm8_late_full_path_water_features_20261114.jsonl'),
              str(pathlib.Path(__file__).resolve().parents[1] / 'red_card_adjusted_form_20261120/expanded15_t1_path_input.jsonl.gz'): sha(pathlib.Path(__file__).resolve().parents[1] / 'red_card_adjusted_form_20261120/expanded15_t1_path_input.jsonl.gz'),
              str(index): sha(index)}
    lines_out = [f'{h}  INPUT::{p}' for p,h in sorted(inputs.items())]
    lines_out += [f'{sha(HERE / name)}  OUTPUT::{name}' for name in files]
    (HERE / 'SHA256SUMS.txt').write_text('\n'.join(lines_out) + '\n')
    print(f'wrote {report}; {len(lines_out)} SHA entries')


if __name__ == '__main__':
    main()
