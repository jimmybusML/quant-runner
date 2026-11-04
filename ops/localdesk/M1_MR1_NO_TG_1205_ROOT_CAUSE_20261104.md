# 2026-11-04 北京时间 12:05 M1/MR1 均执行，但 TG 新单为 0：实证定位

## 口径与真实运行

- Mac 量化控制台 `~/QuantAsiaDesk/state/settings.json` 查询时间：`timezone=Asia/Shanghai`；**用户目前保存** M1、MR1 `schedule_enabled=true`、`schedule_type=times`、`times=12:05`、`tg_enabled=true`；M3/M4 定时关闭。本轮保持用户现有开关，未替用户修改。
- M1 执行 job `20261104T040506Z-200ec79`，UTC 2026-11-04 04:05:06 (北京 12:05:06)，`succeeded`，真实扫描 run `M1_20261104T040508Z`：扫描发现 408 场，11 场在 M1 原赛事与时间规则范围中；新候选1、`errors=0`。派单回执：`new_locks=1`、`telegram_claimed=1`、`telegram_sent=0`、`telegram_unknown=0`。
- M1 **唯一新候选** `fixture_id=203903586`，科特赖克 vs 梅赫伦、2026-11-05 03:30 北京时间，选择梅赫伦 AH 0，扫描记录港赔0.86，原盘标注 Crown。最终发送前重新请求实时 Crown 报价失败，`quote_attempts[0].status=QUOTE_UNAVAILABLE, reason=CROWN_QUOTE_NOT_CURRENT`，`NOTIFICATION_SKIPPED_CROWN_QUOTE`；最终 TG 状态 `SKIPPED_CROWN_QUOTE_UNAVAILABLE`（`skip_reason=QUOTE_UNAVAILABLE`），不存在消息 ID。按用户原有“所有盘口必须 Crown”规则不能使用旧报价替代发单。此状态与 Telegram 传输失败不同。
- MR1 执行 job `20261104T040506Z-8bdcdd9`，同时间启动后完成5步，`succeeded`。Collector status COMPLETE，`snapshots_committed_this_run=1,requests_this_run=10`；策略 `NO_NEW_INPUT`、影子候选0；V6 Cross Market `new_records=0, total_records=18604`；结算步骤 `signals=574, settled=557, added=0, pending=17`；TG 正式通知结果 `eligible=0,sent=0,skipped=0,unknown=0,failed=0`；`STATE_PERSISTED` 成功。本次没有新有效盘口信号，并非 TG 拒绝。

## MR1 原始采集与12:05的时间结构

- 只读核查 `data/prospective-market/shadow-v23/snapshot-index.jsonl` 中在 MR1 2026-11-04T04:05:07 至04:07:42 UTC 执行窗口（前后各90秒）提交的**144条采集状态记录**：`MISSED_WINDOW=143`、`MARKET_UNAVAILABLE=1`、`SNAPSHOT_OK=0`。前者是多时间距开赛观察期已错过，后者是市场不可用；它们**不等于144次真实API报价请求**。对应新输入无法送入策略。
- 原 MR1 策略按开赛前不同 horizon（T72/T48/T36/T24/T18/T12/T6/T3/T1/T0.5）采集；Mac 用户现设每天仅12:05运行一次。若跑的那刻不是某一场的对应采样时间，错过原分段观察窗口是可能的。此处是**原机制与用户希望单次定时运行的实际不匹配**，不是用户要求改变已有模型报价窗口的许可，也不能自动增加扫描次数或一个新的“必须满足的Gate”。
- `m1` 检查实时Crown报价失败，且下一次自动扫描按当前设置将是下一个12:05；此间是否有可验证新报价，尚无数据，不能声称有单未发。若用户希望此后更频繁地确认实时价格，需要**单独提出可选时间安排，等待用户确认**，不要默默改变其12:05设置。

## 与赛果结算问题分开

- 另一轮核查 Mac M1待结8笔、MR1待结17笔；MR1 17笔对应14场，本地 `data/strategy-shadow-ledger/results/*.json` 对应14个FT文件全部不存在。MR1当前 V6 settlement 只读取本地已有FT文件，缺少独立主动拉取缺失赛果程序；因此“运行成功/结算新增0”不能等同于赛果都已经正确核算。M1的独立赛果联网结算路径存在但未被单独排程。M3定时关闭，M4研究为原MR1已结账本。
- 本轮严格**只读核查**，未触发新的M1/MR1模型扫描、TG、订单、赛果写入或GitHub Actions；未修改本机开关、Crown验证策略或数量限制。

## 可选建议（尚未确认，绝不生效）

1. 仅为控制台增加清晰的运行结束摘要“1新候选→0 TG，因为当时报价未核实”和“0新有效市场输入→0 TG”，提高可读性；若需要0单时也发一条TG运行报告，**需用户先批准**，它不是正式下注单，不纳入正式战绩。
2. 将主动检索完场赛果与TG派单解耦的独立补结算任务视为独立可选项；需先有用户确认其是否自动、何时/频率等，绝不把用户未指定的时间规则写入配置。
3. 对“每天12:05单次扫描”与原 MR1 多 horizon采样不匹配问题，向用户列出已观测事实及可选择方案；未经批准不改变12:05、horizon或TG许可。
