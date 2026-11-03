"""Chinese summaries for existing local jobs; historical ledgers remain authoritative."""
import json
import display_data


def summarize(model, action, raw_log):
    lines = raw_log.splitlines()
    if action == "sync":
        return "本机代码已更新，未产生新订单。"
    if action == "report":
        if model == "m3":
            return "M3 六条影子研究线的成绩已重新统计。"
        if model == "m4":
            return "M4 历史联赛优化研究已更新，不是正式下注成绩。"
        return "战绩已更新。请点击对应模型的「看战绩」查看胜负和收益。"
    if action == "settle":
        if model == "mr1":
            for line in reversed(lines):
                if line.startswith("{"):
                    try:
                        x = json.loads(line)
                        if "added" in x and "settled" in x:
                            return "赛果核算完成：本次补结 " + str(x["added"]) + " 笔，已结 " + str(x["settled"]) + " 笔，仍待结 " + str(x.get("pending", "—")) + " 笔。"
                    except ValueError:
                        pass
        return "赛果核算已执行，请打开战绩查看更新结果。"
    if model == "m1":
        for line in reversed(lines):
            if not line.startswith("{"):
                continue
            try:
                x = json.loads(line)
            except ValueError:
                continue
            if x.get("preview_only"):
                return "本次扫描完成，发现 " + str(x.get("new_signals",0)) + " 条新预测。没有发送 Telegram，也没有占用正式订单。"
            if "telegram_sent" in x:
                return "本轮 TG 确认发送 " + str(x.get("telegram_sent", 0)) + " 条，状态未知 " + str(x.get("telegram_unknown",0)) + " 条。"
        return "扫描已执行；尚未取得可核实的新 TG 发送数量。"
    if model == "mr1":
        for line in reversed(lines):
            if "MR1_AH_LOCAL_FORMAL_RESULT " in line:
                try:
                    x = json.loads(line.split("MR1_AH_LOCAL_FORMAL_RESULT ",1)[1])
                    return "MR1 扫描完成，Telegram 回执：" + json.dumps({k:x[k] for k in ("sent","skipped","unknown") if k in x}, ensure_ascii=False)
                except ValueError:
                    pass
        return "MR1 扫描和研究计算已执行；没有发现新的 TG 发送回执。"
    if model == "m3":
        return "M3 预测、结算与账本更新任务已执行。影子成绩请到「看战绩」查看。"
    if model == "m4":
        return "M4 已更新历史联赛对比；并没有生成正式实战订单。"
    return "运行已完成。"


def friendly_error(error):
    s = str(error)
    if "TotalCorner credential" in s or "TOTALCORNER_TOKEN" in s:
        return "还没有在本机保存赛事数据密钥。查看历史战绩不需要它，只有联网扫描和抓取赛果才需要。"
    if "TG enabled" in s or "Telegram credentials" in s or "research TG" in s:
        return "TG 推送已打开，但该模型的 Telegram 账号信息还没存到本机。「连接设置」里可以填写。"
    if "状态不确定" in s or "发送" in s and "TG" in s:
        return s
    if "Step " in s and "exited" in s:
        return "执行中有一个步骤失败，未认定为成功。可以展开「技术详情」查看具体错误。"
    return "运行未成功。可以展开「技术详情」查看原因。"
