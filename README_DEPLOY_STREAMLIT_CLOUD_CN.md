# ETHUSDT A/A+ Monitor — Streamlit Community Cloud 免费部署版

这是云端部署版本。你不需要让本地 Python 访问 Binance，也不需要安装 Anaconda 或本地 VPN。

## 仓库中必须保留的文件
- app.py
- strategy.py
- binance_data.py
- news_risk.py
- alerts.py
- config.yaml
- requirements.txt
- .streamlit/config.toml

## 部署入口
Streamlit Community Cloud 的 Main file path 填：

app.py

## 重要
- 不需要 Binance API Key。
- 不要把 Binance Secret/API Key、助记词、账户密码上传到 GitHub。
- 本项目不会自动下单。
- 浏览器通知需要在网页中点击一次 `Enable browser alerts` 并授权。
- Community Cloud 更适合“随时打开网页实时看”，并不是高可靠 24/7 后台守护进程。
