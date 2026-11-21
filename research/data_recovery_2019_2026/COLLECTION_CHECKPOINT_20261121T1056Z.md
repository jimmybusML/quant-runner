# 全历史补采进度快照｜2026-11-21 10:56 UTC

仅记录历史赛事、赛果与Crown AH数据收集进度；不是任务完成报告。

- Crown SQLite只读计数：historical movement有报价52,919 FID / 4,421,110行；`NO_CROWN_AH_QUOTES` 49,561 FID。10:50 UTC后新写入18条无AH报价capture，没有新增movement报价行。
- 第二批原清单11,703个FID。修复后的安全窗口驱动于10:54:26 UTC生成恢复清单（SHA256 `6d02f8abc082ff90299f38d6cd5e3159a131f2db66c81fad2ab95fe00a82cdd4`，当时剩11,650个）并启动collector PID 80846；截至10:56:30 UTC，追加日志累计150行/72个唯一FID，最新唯一状态为51 REUSED_DB、2 SAVED、1 FETCH_FAILED、18 NO_CROWN_AH_QUOTES，20个唯一FID带HTTP实际收件时间。正在从已处理前缀继续。
- 对5个新 `NO_CROWN_AH_QUOTES` 原始响应逐场读取并校验SHA：均为有效成功响应、FID匹配、存在Crown bookmaker，但`asian_list`为空。只能结论为这些响应时点未返回AH movement，不能推断其他历史接口或时点永远无报价。
- 安全驱动仍监控已知定时TotalCorner任务；不停止生产任务、不改请求频率、不改生产collector。剩余候选及错误在完成第一轮后单独续试。
- 完整机器快照：`collection_progress_snapshot_20261121T1056Z.json`。全联赛覆盖审计仍基于10:23 UTC的库存快照，等待当前回补完成后再重新构建。