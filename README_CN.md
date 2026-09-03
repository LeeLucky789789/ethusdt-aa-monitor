# ETHUSDT A/A+ 实时策略监控面板

这个版本用于 Windows 本地运行，目标是把当前讨论的策略做成你平时可以自己随时查看的实时面板。

## 已包含
- Binance USDⓈ-M Futures 公共数据，不需要 API Key
- 15m / 1h / 4h 多周期结构
- 成交量、Taker 主动买卖、OI、资金费率
- 全市场多空比
- Top Trader 大户账户与大户持仓多空比
- 实时订单簿深度
- 事件/新闻风险启发式过滤
- A+/A/B/C 评分
- “为什么现在不是 A/A+”
- Entry / SL / TP1 / TP2 / TP3
- 1000 RMB + 13×逐仓 + 固定风险预算仓位计算
- 当前空单 0.160 ETH @ 2413.54 的持仓管理
- Windows 桌面通知 + 声音提醒 + 浏览器 Notification/WebAudio 尝试
- 6–12 小时同结构去重
- 不自动下单

## Windows 运行
1. 安装 Python 3.11 或 3.12，并勾选 Add Python to PATH。
2. 解压本项目。
3. 双击 `run.bat`。v1.1 会先等待本地服务器真正启动，再打开浏览器，避免 `ERR_CONNECTION_REFUSED`。
4. 第一次运行会自动创建 `.venv` 并安装依赖，可能需要几分钟。
5. 浏览器会打开 `http://localhost:8501`。
6. 页面顶部点击 `Enable browser alerts`，允许浏览器通知/声音。

以后直接双击 `run.bat` 即可。

## 配置
编辑 `config.yaml`：
- `refresh_seconds`: 默认 60 秒
- `signal_cooldown_hours`: 默认 8 小时
- `equity_rmb`: 默认 1000
- `leverage`: 默认 13
- `risk_A_pct`: 默认 3%
- `risk_Aplus_pct`: 默认 5%
- `rmb_per_usdt`: RMB/USDT 近似换算
- `position`: 当前持仓
- `news`: 新闻风险关键词

## 策略层级
### 核心硬条件
A/A+ 必须先满足：
1. 4h 方向
2. 1h 结构
3. 15m 实际触发
4. 关键位
5. R:R 与目标空间

### 加权条件
只做加减分，不要求全部 AND：
- 成交量
- Taker
- OI
- Funding
- 全市场多空比
- Top Trader
- Order Book
- 拥挤/清算风险

### 事件风险
分为：
- 正常
- 升高
- 冲击

新闻模块只是启发式过滤。真正重大事件时，可以在 `config.yaml` 临时手动设置：

```yaml
news:
  manual_event_risk: shock
```

恢复自动：
```yaml
manual_event_risk: auto
```

## 重要限制
1. 历史订单簿不能像 K 线一样完整回放，因此盘口主要用于实时确认。
2. Google News RSS 可能因网络环境读取失败；失败时不会凭空提高评级。
3. 浏览器 Notification API 受浏览器安全策略影响；如果被拦截，Windows 桌面通知、Streamlit toast 和提示音仍可工作。
4. 这是监控与风险预算工具，不保证盈利，也不会提交真实订单。
5. 第一版策略评分是规则化实现，不等于正式 1–2 年 walk-forward 回测后的最终参数。

## 安全
本项目不需要 Binance API Key、Secret、助记词或账户密码。不要把这些信息写进脚本。


## 如果出现 localhost 拒绝连接

v1.0 的启动脚本会先打开浏览器、再启动 Streamlit，因此首次运行可能短暂出现 `ERR_CONNECTION_REFUSED`。v1.1 已修复为：

`检查 Python → 创建环境 → 安装依赖 → 启动 Streamlit → 检测 8501 端口 → 浏览器打开`

请保持黑色命令窗口开启。关闭命令窗口会停止本地监控服务。

若 v1.1 仍不能打开，双击 `diagnose.bat`，把诊断窗口截图发给 ChatGPT。
