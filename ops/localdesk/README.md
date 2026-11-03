# 量化亚洲盘：Mac 本机统一控制台（2026-11-03）

本目录备份已经实际安装到使用者 Mac 的**本机控制台源代码**。该控制台仅监听 `127.0.0.1:8765`，前端为 `web/index.html`，Python 后台为 `app.py`，无需云端站点或创建新仓库。

## 已安装且已验证的环境（特定使用者 Mac）

- 本机文件 `~/QuantAsiaDesk/`；桌面快捷入口 `~/Desktop/量化亚洲盘控制台.command`；Mac 登录自动启动的 LaunchAgent `~/Library/LaunchAgents/com.quantasia.localdesk.plist`。
- `~/QuantAsiaDesk/repos/m1` 是现有私有 `totalcorner-research-bridge/master` 的本机副本，`repos/mr1` 是原私有 `mr1-shadow/master` 副本；`repos/runner` 是原公开 `quant-runner/main` 副本，承载 M3、M4 研究。没有新建 GitHub 仓库，也没有迁移或删除正式账本。
- `~/QuantAsiaDesk/venv`（Python 3.12）已安装 `penaltyblog==1.13.1`、numpy、pandas、scipy、requests；MR1 `npm ci` 已完成。macOS 自带 launchd 启动 Python 3.9 HTTP 服务，页面中文、响应式；用户可以通过浏览器更改各模型定时方式（指定 HH:MM 或间隔），手动运行、结算、报告、同步代码及查看本机执行日志。
- 初始配置全部 `schedule_enabled=false`，M1/MR1 `tg_enabled=false`（不接管生产并避免双重派单）。M3/M4 仍严格是**影子研究**，没有正式 Telegram 发送入口。M1 带 TG 时调用原 `m1_immediate_delivery.py`；本机运行前复用已确认的 `ops/m1_ah_ev_cap.py`，EV >=0.10 的模型原选单过滤保持不变。M1 无 TG 时的扫描输出和信号身份独立保存在 `~/QuantAsiaDesk/state/m1_preview/`。MR1 带 TG 时复用原 `v6-ah-formal-notify.js` 与 2026-10-19 activation，并使用原 `persist-github-state.js` 回写；普通 MR1 运行仍跟随 V6 Shadow/Forward/Settlement 逻辑。
- M3 本地前瞻复用原有 `research/m3/` 代码、原 M1 私有历史缓存和 TotalCorner API；使用 `segmented_ledger.py` 重建 base + segments，模拟订单按用户确认的 `fixture_identity_id×model×market` 单场唯一口径，EV 只记录、不作为门槛。M4 的按钮真实执行 `research/m4/mr1_two_league_pass_study.py`，输入本地 MR1 正式已结算账本，仅研究、不执行 Pass。
- 2026-11-03 本机真实界面操作成功：M1 正式报告计算、MR1 已保存数据 557 单结算核对、M3 1,530 唯一影子单 / 1,050 已结算 / +0.275U 重算、M4 从 557 笔 MR1 结算记录生成研究输出。`git pull --ff-only` 同步公开 Runner 后，本机 `segmented_ledger materialize` 实际组合 163,546 条历史事件和 2 个新增分段文件。

## 尚未完成的生产切换（不可宣称已恢复）

- 使用者尚未通过本机页面配置 `TOTALCORNER_TOKEN`、M1/MR1 Telegram 凭证到 macOS 钥匙串。不会自动读取、展示、发送旧私有 Secrets，也不会把未配置的本机任务报告为成功。请用户**仅在本机网页**输入，不得贴入聊天。需要用户操作完成后再核对真实 Crown 扫描、TG 发送回执和正式账本回写。
- 公开 M3 GitHub 工作流的 100 MiB 账本增长问题已修复：commit `cd97fdb` 的不可变分段方案，真实 run `41602048717` 的**原先 Persist fixture inventory 步骤成功**，新增 2 个 segment 已写入 `main`（之后真实 run 仍在检出私有 M1 缓存步骤失败，原有 `PRIVATE_REPO_TOKEN` 尚无修复）；本机可直接读取已克隆的 M1 缓存，不需要公开 Runner 从另一私有仓库 checkout。
- 在上述联网真实运行及多次重复执行/账本对账完成前，**不得关闭 GitHub 原有定时任务**，也不能宣称整个生产已从 GitHub 迁移。用户有完全本机调度和 TG 开关控制权；开启本机正式 TG 前需要识别旧任务是否仍会并发发单。
- 用户已明确的 M1/MR1 Crown 来源和所有其他规则保持不变；不自动把 M3/M4 发 TG，不自动新建任何 Gate、投注数量上限或筛选条件。

## 代码部署

将本目录的 `app.py`、`web/`、`scripts/` 复制到 `~/QuantAsiaDesk/`，再在 `~/QuantAsiaDesk/repos/` 使用原有 GitHub 身份检出 M1、MR1 和 Runner 仓库。macOS launchd 启动 `app.py`，浏览器打开 `http://127.0.0.1:8765`。完整依赖安装与进程设置请参考本项目最新 `PROJECT_HANDOFF.md`；本目录不包含用户凭证、用户名或生产账本原始文件。
