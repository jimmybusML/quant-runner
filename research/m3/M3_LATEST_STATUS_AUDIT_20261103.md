# M3 当前运行、影子战绩及研究状态（2026-11-03）

本报告只读取公开 `quant-runner/main` 的 M3 账本、现有研究输出与 GitHub Actions；未修改任何模型、影子规则、Telegram 或历史订单。**M3 始终研究影子，没有正式 TG 订单或正式实战 ROI。**

## 一、实时工作流事实

- M3 主前瞻 `m3-totalcorner-forward-ev.yml` 最近 5 次运行均 failure：最新 [41592553780](https://github.com/ljm198964-alt/quant-runner/actions/runs/41592553780)（2026-11-03T06:51:42Z），上一运行 41571372844 亦失败。最新 run 已成功 checkout 公共仓库、安装模型依赖、幂等单测并执行未来赛程盘点，但在 `Persist fixture inventory before slower model and odds phases` 退出。后续 M1 缓存检出、模型拟合、正式影子订单生成和 FT 补结因该步失败被 skip。第二次 always 持久化也失败，故整个 run 不成功。
- `persist_append_ledger.py` 错误为 `RuntimeError: concurrent ledger persistence failed after retries`。脚本对每次 `git push` 非零退出只做 retry，不打印实际 stderr，因此此字样**不证明真的发生 Git 并发冲突**。
- 通过下载最新运行原始 Artifact `m3-fresh-totalcorner-ev-41592553780` 复查：远端 Git blob `forward_ev_ledger.jsonl` 104,477,212 字节，未提交的 runner 候选文件 105,176,572 字节，**超过 GitHub 普通 Git 文件 100 MiB 强制上限 104,857,600 字节，共超 318,972 字节**。单文件上限与失败位置高度一致。现有候选比已保存历史多 **1,061 条 `M3_TOTALCORNER_FUTURE_INVENTORY_V1`**，均来自 run 41592553780-1；属于临时 Artifact 未推送事件，不应当成已写入生产账本。GitHub 官方文档明确 100 MiB 普通文件限制：https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github 。若要确定远端拒收的原始错误，需在现有持久化脚本记录（脱敏后的）push stderr 后再复跑。本次未修改任何工作流。
- 主账本最后一次有新保存提交 `cdd954c4fe`，2026-11-02T00:52:31Z；其中最新预测记录 `forecasted_at_utc` 为 **2026-10-30T11:01:01.736Z**。当前不能宣称已恢复自动出新的 M3 预测或生成新的有效影子订单。
- `m3-forward-schedule-watchdog.yml` 最近 41592539388 success，日志实际发现 2026-11-03T04:00Z 调度窗口缺失并成功申请调度补跑；但补跑本身仍 failure，不等于成功恢复。`m3-price-followup.yml` 最近 41558274331 success，真实回执 `eligible_fixtures=0, attempted_fixtures=0, snapshot_events=0, errors=[]`，因此该成功**没有产生新的盘口观察**。
- `m3-totalcorner-settle-only.yml` 最近 41177921241（2026-10-31）success，当次新增 324 条结算事件，`formal_bets=0`，严格属于影子研究；`m3-oos-stability.yml` 最近 41570306443 failure，日志 `AssertionError: 2 != 1`；`m3-controlled-evolution.yml` 最近 41407574456（11-02）success，不能混成主前瞻 success。
- M3 主前瞻后续还有检出私有 M1 结果缓存的 `actions/checkout` 步骤，它使用公开 Runner 的 `PRIVATE_REPO_TOKEN`；该凭证在 M1/MR1 正式链路已证实失败。即使排除当前单文件超限故障，仍应验证这个后续依赖，不能现在宣称它已成功。

## 二、单场唯一口径重新核算 M3 影子实盘模拟

数据源：已推送 `main` 的 `research/m3/results/totalcorner/forward_ev_ledger.jsonl`（161,312 条事件），此轮本地逐条读取 `M3_SHADOW_ORDER_V1` 与 `M3_TOTALCORNER_FORWARD_SETTLEMENT_V1`，只通过 `shadow_order_event_id` 与对应影子单进行绑定；订单按用户明确确认的 **`fixture_identity_id × model × market`** 取最早 `forecasted_at_utc`，保留历史原始事件不做任何删除或覆盖。

- 原始 `M3_SHADOW_ORDER_V1` 历史事件 **3,348 笔**，该唯一口径筛出 **1,530 笔**（255 场独立比赛 × 3 模型 × AH/OU），其余 **1,818 笔**是同比赛模型盘口的后续历史订单事件。原始事件都保存供审计，不能作为有效新增独立订单反复计成绩。
- 去重后 **1,050 笔已结算、480 笔待结算**，每条模型盘口线均 **255 笔订单、175 已结、80 待结**；六条线净合计 **+0.275U、ROI +0.0262%**。单笔统一影子资金 1U；多模型/盘口/同场结果彼此相关，不代表1050场独立比赛。

| 模型 | 盘口 | 有效影子单 | 已结 | 待结 | 净 U | ROI |
|---|---|---:|---:|---:|---:|---:|
| Poisson | AH | 255 | 175 | 80 | +0.2125 | +0.121% |
| Poisson | OU | 255 | 175 | 80 | -0.4875 | -0.279% |
| Dixon-Coles | AH | 255 | 175 | 80 | -3.0250 | -1.729% |
| Dixon-Coles | OU | 255 | 175 | 80 | -0.4875 | -0.279% |
| Bivariate Poisson | AH | 255 | 175 | 80 | +2.9500 | +1.686% |
| Bivariate Poisson | OU | 255 | 175 | 80 | +1.1125 | +0.636% |
| **合计** | | **1530** | **1050** | **480** | **+0.275** | **+0.026%** |

注意：自动输出 `shadow_performance_summary.json` 生成于 2026-11-02T23:11:31Z、统计全部 3,348 历史原始订单事件的净收益，**不符合用户更新的“同场×模型×盘口只记一单”统计口径**，本报告优先采用上述唯一身份重算。M3 的报价当前按用户决定仍是 **TotalCorner 默认盘口（NOT CROWN）**，不混入 M1/MR1 Crown 正式实战。

## 三、AH 反打、盘口后续与模型版本

- 最近 `M3 AH Reverse Research` run 41502280991 success，基于相同 255 场、每模型 AH 175 已结，模拟反打均为亏损：Poisson **-13.275U / -7.59%**，Dixon-Coles **-10.0375U / -5.74%**，Bivariate **-16.0125U / -9.15%**。此前用户明确“先观察、不把反打直接加为正式策略”，本次无规则变更。
- 价格 followup 任务 11/03 最新 run 41558274331 执行成功但 **0 eligible、0 attempted、0 snapshot events**；不能据此报“降水概率已验证”。账本历史另有 2,036 个价格快照事件，需严格做订单与时间配对才能判断实际降水发生率，不能把事件数量当可验证投注单数量。
- `evolution_rolling_registry.json` 最新写入 2026-11-02T07:38:24Z，Poisson、Dixon-Coles、Bivariate Poisson 三者 `rolling_shadow_active` 均为 `rolling_4y`，该轮 `decision=HOLD`，各自候选已配对场次 7；HOLD 意味着没有进一步切换版本，不是三个模型自动进化已被证实盈利。

## 四、接续工作（未授权的建议不是生产规则）

1. **建议**：把 100MiB 单文件 append-only JSONL 从反复整文件 Git push 改为可追加的分段账本或存储对象，完整保留历史 `event_id`、订单身份、结算关系，并保持公开仓库这一既定方向。是存储技术修复，非新增任何模型、数量或盈利 Gate；在实际实施前应确认用户希望采取哪种持久化方式。
2. **建议**：暴露当前持久化步骤底层 `git push` 错误以确认上限，修复后用真实 workflow 验证主链继续执行、生成新预测、单场唯一影子订单、完整写入，再核对下游 M1 cache 权限是否再次阻断。
3. 继续以每条真实新增订单的 FT 和后续报价证据观察模型、降水、AH 反打。**没有任何 M3 TG 正式投注。**
