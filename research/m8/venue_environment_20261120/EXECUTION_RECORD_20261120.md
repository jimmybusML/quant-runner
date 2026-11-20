# 执行记录

- `python3 research/m8/venue_environment_20261120/m8_venue_environment_20261120.py`：本轮研究脚本此前已完成全量历史重放；候选与逐年数量、模型结果见主报告和 `results_20261120.json`。
- `python3 research/m8/venue_environment_20261120/verify_venue_crown_ft_20261120.py`：本轮再次执行两次，1,673/5,978个候选FID原始 Crown/FT 检查通过，三模型共5,019笔结算复核通过；4,305个FID缺本地原始响应，覆盖未全。
- `python3 research/m8/venue_environment_20261120/build_deliverables_20261120.py`：已重建报告、输入输出SHA清单与执行记录。
- 独立校验器输出gzip现固定`mtime=0`；两次重复运行产生相同字节和SHA256 `46bdf28ab7f0258902c628269578bf4f41104c1f89de686fbc7bd6c48d7fd7df`。
- 数据范围：5,978个八组外唯一FID；2024/2025/2026分别1,962/2,723/1,293场。真实HTTP Crown收据与候选交集0。
- 清单核对：11个输出和8个外部输入SHA均匹配；5,180份已保存赛程页的逐文件SHA另见 `SCHEDULE_FILE_SHA256_20261120.json`。
- 本轮未运行正式GitHub Actions或生产workflow；正式TG派单0、账本回写0、生产采集/调度改动0。
