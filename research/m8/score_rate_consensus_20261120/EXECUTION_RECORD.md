# 执行记录

- 执行日期：2026-11-20 Asia/Shanghai
- 分支：`research/m8-m9-groups`
- 研究输入：`m8_late_full_path_water_features_20261114.jsonl`、`m8_independent_score_strength_20261114.jsonl`、冻结 `historical_membership.jsonl`、MR1实际收据归档、原始Crown报价响应映射。
- 主计算：`python3 research/m8/score_rate_consensus_20261120/run_score_rate_consensus.py`，退出码0。输出39,101唯一FID逐场账本及全期、年度、ISO周、联赛、方法交集和冻结八组合并统计。
- 独立审计：`python3 research/m8/score_rate_consensus_20261120/verify_score_rate_consensus.py`，退出码0。重新结算156,404个FID×方法行，差异0；重复FID 0；2024–2026八组外候选21,454与冻结10,294名单交集0。原始Crown T−1报价对39,101FID均找到，39,097线价水完全一致，4个水位差异例子已保存在 `independent_verification.json`。
- 真实receipt交集：候选FID中873场存在于MR1 HTTP Crown收据归档。但比分率特征无首次收到时点/收据快照，故有效实时特征重放0；历史盘口回放不代表TG成交或正式账本。
- 生产边界：未运行生产workflow/Actions；未修改M8八组、M9、M1/MR1、Crown采集链、Telegram或正式账本；正式订单0，账本写入0。
- 当前交付只增加研究目录文件和 PROJECT_HANDOFF 交接，不上传原始HTTP response body。
- 公开提交及PR更新记录见本目录 `SHA256SUMS.txt` 与本轮最终Git状态。
