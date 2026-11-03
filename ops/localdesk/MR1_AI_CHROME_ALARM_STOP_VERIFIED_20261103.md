# MR1 AI TotalCorner 自动弹出浏览器：本机旧 Chrome 定时器彻底清除

操作时间：2026-11-03 20:58 +08:00，北京时间。

## 最新用户指令与故障根因

用户明确要求停止 Mac 上**反复自动打开 TotalCorner 网站**，保留其他浏览器页面和量化控制台。此前仅修改 `~/Desktop/mr1-ai/background.js` 和停止两个 macOS LaunchAgent，但 Chrome 当前进程仍加载扩展并保有旧的每小时 `mr1-ai-hourly` 事件，因此**改文件并不等于清除 Chrome 内存中的旧定时器**。

已从用户当前 Mac `~/Library/Application Support/Google/Chrome/Default/Secure Preferences` 确认 Chrome `Default` profile 的 MR1 AI Unpacked 扩展仍安装，ID `peplalmabefbpaihaeehmbncibfgopnf`，真实加载路径 `~/Desktop/mr1-ai`。在真实 Chrome 扩展详情页看到 MR1 AI TotalCorner Collector 仍处于「已启用」状态；因此必须清除**真实扩展运行状态**，而不是仅修改静态源码或停止不相关 Chrome 进程。

## 已完成实际操作及证据

1. 原来每小时创建两条 TotalCorner AI Picks 标签的代码已在真实加载目录 `~/Desktop/mr1-ai/background.js` 去除：`chrome.alarms.create` 和 `chrome.tabs.create` 均不存在，保留手动抓取逻辑。本轮再次检查确认。源项目副本亦已去除自动开页。
2. 前一轮原 `com.mr1.ai.extension-bridge` 和 `com.mr1.shadow-market-collector` 两个 launchd agent 已 `bootout` 并移出 `~/Library/LaunchAgents/`；本轮 `launchctl list` 再确认两个均未加载。
3. 本轮通过真正已安装扩展自身的 `chrome-extension://peplalmabefbpaihaeehmbncibfgopnf/stop-auto-open.html` 调用 `chrome.alarms.getAll()`、`chrome.alarms.clearAll()`、标记 `chrome.storage.local` 为已停用，并 `chrome.runtime.reload()` 重新加载已去除自动开页的后台脚本。这一步直接清理当前 Chrome 内存中的**持久化定时器**，不是静态文件修改。
4. 扩展重新加载后，又用独立 `verify-auto-open.html` 在同一个真实扩展上下文查询 `chrome.alarms.getAll()`；返回**没有 `mr1-ai-hourly`**，并在 Chrome `Local Extension Settings/peplalmabefbpaihaeehmbncibfgopnf` LevelDB 证据中写入 `mr1AutoOpenVerifiedAfterReload=true` 和 `mr1ActiveAlarmCount=0`。本机原存储有可查的证明状态。
5. 临时自检页面中的脚本只关闭由本次操作创建的 `stop-auto-open.html` / `verify-auto-open.html` 页面；**没有关闭用户自己的 Chrome、其他标签、量化控制台**。控制台 `http://127.0.0.1:8765` 验证 HTTP200，Mac 用户原有模型自动调度不受影响。

## 当前真实状态与范围

- Chrome MR1 AI 的旧周期 alarm 已实际清零，且已重载没有自动开页功能的后台代码。**MR1 AI TotalCorner 自动弹窗来源已停止**。
- Chrome 扩展本身仍显示为「已启用」，只是停掉了自动访问 TotalCorner 的行为；用户要手动使用时保留现有功能。不要把“自动弹窗已关闭”混同为“扩展已卸载”。
- 不修改模型、盘口来源、TG、历史订单或赛果，GitHub 已停的 TG 发单入口保持关闭。其他系统/插件自身可能仍能由自己的独立动作打开浏览器，本轮不据此宣称整个系统永远不会开任何网页。
- 若以后再次出现同样 URL 自动弹出，应优先确认是否该扩展被重新安装旧版本或存在另一个独立开页源；**不应重建此前的自动时钟任务**，用户已要求停止。
