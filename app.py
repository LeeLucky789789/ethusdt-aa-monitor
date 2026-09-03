from __future__ import annotations
import json,time
from pathlib import Path
import yaml
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go

from binance_data import BinancePublicData
from news_risk import assess_news_risk
from strategy import evaluate
from alerts import play_sound,desktop_notify,browser_alert_html,permission_button_html

st.set_page_config(page_title="ETHUSDT A/A+ Monitor",layout="wide",page_icon="Ξ")
ROOT=Path(__file__).resolve().parent
CFG=yaml.safe_load((ROOT/"config.yaml").read_text(encoding="utf-8"))
SYMBOL=CFG["app"]["symbol"]; STATE_FILE=ROOT/CFG["app"]["database_file"]

@st.cache_data(ttl=50,show_spinner=False)
def fetch_all(symbol,n):
    net=CFG.get("network",{})
    b=BinancePublicData(
        timeout=net.get("timeout_seconds",15),
        use_windows_system_proxy=net.get("use_windows_system_proxy",True),
        custom_proxy=net.get("custom_proxy","")
    )
    b.ping()
    return {
        "15m":b.klines(symbol,"15m",n),
        "1h":b.klines(symbol,"1h",n),
        "4h":b.klines(symbol,"4h",n),
        "funding":b.funding_history(symbol,30),
        "oi":b.open_interest_hist(symbol,"1h",100),
        "global_ls":b.global_long_short(symbol,"1h",100),
        "top_account_ls":b.top_account_long_short(symbol,"1h",100),
        "top_pos_ls":b.top_position_long_short(symbol,"1h",100),
        "taker":b.taker_buy_sell(symbol,"1h",100),
        "orderbook":b.order_book(symbol,500),
        "mark":b.mark_price(symbol),
    }

def load_state():
    if STATE_FILE.exists():
        try:return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:pass
    return {"last_alert_ts":0,"last_alert_grade":"","last_alert_side":"","last_alert_key":""}

def save_state(s):
    STATE_FILE.write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding="utf-8")

def candle_chart(df,title):
    d=df.tail(160)
    fig=go.Figure(data=[go.Candlestick(x=d["open_time"],open=d["open"],high=d["high"],low=d["low"],close=d["close"],name=title)])
    fig.update_layout(height=380,margin=dict(l=10,r=10,t=35,b=10),xaxis_rangeslider_visible=False,title=title)
    return fig

st.title("ETHUSDT A/A+ 实时策略监控面板")
st.caption("Streamlit Community Cloud 版｜公共市场数据｜不需要 API Key｜不自动下单｜默认每 60 秒刷新")

a,b,c=st.columns([1,1,2])
with a:
    if st.button("立即刷新",use_container_width=True):
        st.cache_data.clear(); st.rerun()
with b:
    auto=st.toggle("自动刷新",value=True)
with c:
    components.html(permission_button_html(),height=48)

try:
    data=fetch_all(SYMBOL,CFG["app"]["lookback_klines"])
    news=assess_news_risk(CFG["news"])
    sig=evaluate(data,CFG,event_risk=news.level,event_reason=news.reason)
except Exception as e:
    st.error(f"数据读取/策略计算失败：{e}")
    st.warning(
        "程序已经正常启动，但当前电脑无法连接 Binance Futures 公共接口。"
        "这通常是网络、地区限制、代理/VPN、公司/校园防火墙或 DNS 路由问题，不是策略代码报错。"
    )
    st.markdown("""
**按这个顺序排查：**

1. 在同一台电脑浏览器测试 Binance Futures API 是否能访问；
2. 如果你平时使用 Clash / V2Ray / VPN，请先开启后点击“立即刷新”；
3. v1.4 会自动读取 Windows 系统代理；
4. 如果仍不行，在 `config.yaml` 的 `network.custom_proxy` 填入本机代理，例如 `http://127.0.0.1:7890`；
5. 双击 `TEST_BINANCE_CONNECTION_v1_4.bat`，把输出截图发给我。
""")
    st.stop()

icon={"A+":"🔥","A":"✅","B":"🟡","C":"⚪"}.get(sig.grade,"")
side_cn="做多" if sig.side=="LONG" else "做空"
m1,m2,m3,m4,m5=st.columns(5)
m1.metric("当前价格",f"{sig.price:,.2f} USDT")
m2.metric("信号等级",f"{icon} {sig.grade}")
m3.metric("综合评分",f"{sig.score}/100")
m4.metric("方向",side_cn)
m5.metric("事件风险",sig.event_risk)

if sig.grade in {"A","A+"}:
    st.success(f"{icon} {sig.grade} {side_cn}｜R:R≈{sig.rr:.2f}｜{'不要追单' if sig.do_not_chase else '等待入场区确认'}")
else:
    st.info(f"当前 {sig.grade}：不作为新开仓提醒。下方显示还差什么条件。")

c1,c2,c3=st.columns(3)
with c1:
    st.subheader("核心硬条件")
    st.write(f"4H：**{sig.trend_4h}**")
    st.write(f"1H：**{sig.trend_1h}**")
    st.write(f"15m触发：**{sig.trigger_15m}**")
    st.write(f"关键位：{sig.key_level}")
    st.write(f"硬条件：{'✅ 通过' if sig.hard_conditions_ok else '❌ 未通过'}")
with c2:
    st.subheader("量价 / 衍生品")
    st.write(f"成交量：**{sig.volume_state}**")
    st.write(f"Taker：**{sig.taker_state}**")
    st.write(f"OI：**{sig.oi_state}**")
    st.write(f"资金费率：**{sig.funding_state}**")
with c3:
    st.subheader("拥挤 / 盘口")
    st.write(sig.crowd_state)
    st.write(sig.top_trader_state)
    st.write(f"订单簿：**{sig.orderbook_state}**")
    st.write(f"事件：**{sig.event_reason}**")

st.subheader("为什么现在是这个等级")
left,right=st.columns(2)
with left:
    st.markdown("**加分依据**")
    if sig.notes:
        for x in sig.notes: st.write("✓",x)
    else: st.write("暂无明显强共振")
with right:
    st.markdown("**升级还缺什么**")
    if sig.missing_for_upgrade:
        for x in dict.fromkeys(sig.missing_for_upgrade): st.write("✗",x)
    else: st.write("核心条件已较完整")

st.subheader("交易计划")
p1,p2,p3,p4,p5=st.columns(5)
p1.metric("Entry",f"{sig.entry_low:.2f}–{sig.entry_high:.2f}")
p2.metric("Stop",f"{sig.stop:.2f}")
p3.metric("TP1",f"{sig.tp1:.2f}")
p4.metric("TP2",f"{sig.tp2:.2f}")
p5.metric("TP3",f"{sig.tp3:.2f}" if sig.tp3 else "—")

r1,r2,r3,r4=st.columns(4)
r1.metric("允许风险",f"¥{sig.risk_rmb:.1f}")
r2.metric("建议名义仓位",f"¥{sig.notional_rmb:.0f}")
r3.metric("建议保证金",f"¥{sig.margin_rmb:.0f}")
r4.metric("建议数量",f"{sig.qty_eth:.4f} ETH")

x1,x2,x3,x4=st.columns(4)
x1.metric("止损预计亏损",f"¥{sig.expected_loss_rmb:.1f}")
x2.metric("TP1预计盈利",f"¥{sig.expected_profit_tp1_rmb:.1f}")
x3.metric("TP2预计盈利",f"¥{sig.expected_profit_tp2_rmb:.1f}")
x4.metric("TP3预计盈利",f"¥{sig.expected_profit_tp3_rmb:.1f}" if sig.expected_profit_tp3_rmb else "—")

st.code(f"""【币安直接填写版】
交易对：ETHUSDT 永续
方向：{'BUY / 做多' if sig.side=='LONG' else 'SELL / 做空'}
保证金模式：逐仓
杠杆：{CFG['account']['leverage']}×
订单类型：限价 / 等待15m触发确认
参考开仓价：{sig.entry_low:.2f}–{sig.entry_high:.2f} USDT
建议数量：{sig.qty_eth:.4f} ETH
建议占用保证金：约 {sig.margin_rmb:.0f} RMB
止损 SL：{sig.stop:.2f} USDT
止盈 TP1：{sig.tp1:.2f} USDT｜建议减仓 30%
止盈 TP2：{sig.tp2:.2f} USDT｜建议减仓 40%
止盈 TP3：{sig.tp3:.2f} USDT｜剩余仓位
最大预计亏损：约 {sig.expected_loss_rmb:.1f} RMB
事件风险：{sig.event_risk}
盘口/拥挤：{sig.orderbook_state}；{sig.crowd_state}；{sig.top_trader_state}
执行提示：{'当前不要下单/不要追单' if (sig.grade not in {'A','A+'} or sig.do_not_chase or sig.event_risk=='冲击') else '核对方向、数量、逐仓、止损和止盈后再手动确认'}
""",language=None)

if CFG["position"].get("enabled",False):
    pos=CFG["position"]
    st.subheader("当前持仓管理")
    mark=float(data["mark"]["markPrice"]); entry=float(pos["entry_price"]); qty=float(pos["qty_eth"])
    pnl_usdt=(entry-mark)*qty if pos["side"]=="SHORT" else (mark-entry)*qty
    pnl_rmb=pnl_usdt*CFG["account"]["rmb_per_usdt"]
    q1,q2,q3,q4=st.columns(4)
    q1.metric("已知仓位",f"{pos['side']} {qty:.3f} ETH")
    q2.metric("开仓均价",f"{entry:.2f}")
    q3.metric("Mark",f"{mark:.2f}")
    q4.metric("估算未实现盈亏",f"¥{pnl_rmb:.1f}")
    action="继续持有 / 不加仓"; op_qty=0.0; new_stop=float(pos["invalidation_high"])
    if mark<=pos["tp3"]:
        action="大部分止盈"; op_qty=qty*.70
    elif mark<=pos["tp2"]:
        action="第二档减仓 30%–40%"; op_qty=qty*pos["tp2_reduce_pct"]; new_stop=entry
    elif mark<=pos["tp1"]:
        action="第一档减仓 25%–30%，并评估止损移至开仓价附近"; op_qty=qty*pos["tp1_reduce_pct"]; new_stop=entry
    elif mark>=pos["invalidation_low"]:
        action="空头逻辑接近/进入失效区，优先减仓或平仓"; op_qty=qty
    st.warning(f"建议动作：**{action}**")
    st.code(f"""【币安持仓操作版】
当前仓位：{pos['side']} {qty:.3f} ETH @ {entry:.2f}
建议动作：{action}
建议操作数量：{op_qty:.3f} ETH
新的止损价：{new_stop:.2f} USDT
TP1：{pos['tp1']}｜TP2：{pos['tp2']}｜TP3：{pos['tp3']}
事件风险：{sig.event_risk}
盘口/多空比：{sig.orderbook_state}；{sig.crowd_state}
""",language=None)

tabs=st.tabs(["15m","1h","4h","新闻风险"])
with tabs[0]: st.plotly_chart(candle_chart(data["15m"],"ETHUSDT 15m"),use_container_width=True)
with tabs[1]: st.plotly_chart(candle_chart(data["1h"],"ETHUSDT 1h"),use_container_width=True)
with tabs[2]: st.plotly_chart(candle_chart(data["4h"],"ETHUSDT 4h"),use_container_width=True)
with tabs[3]:
    st.write(f"事件风险：**{news.level}**")
    st.write(news.reason)
    for h in news.headlines[:8]: st.write("•",h)

state=load_state(); now=time.time(); cooldown=CFG["app"]["signal_cooldown_hours"]*3600
same=(state.get("last_alert_side")==sig.side and state.get("last_alert_key")==sig.key_level)
upgrade=(state.get("last_alert_grade")=="A" and sig.grade=="A+")
eligible=sig.grade in {"A","A+"} and sig.event_risk!="冲击" and not sig.do_not_chase
should_alert=eligible and (not same or now-state.get("last_alert_ts",0)>cooldown or upgrade)

if should_alert:
    title=f"ETHUSDT {sig.grade} {side_cn}"
    msg=f"{sig.price:.2f}｜Score {sig.score}｜Entry {sig.entry_low:.0f}-{sig.entry_high:.0f}｜SL {sig.stop:.0f}"
    play_sound(sig.grade,CFG["alerts"])
    desktop_notify(title,msg,CFG["alerts"].get("enable_desktop_notification",True))
    html=browser_alert_html(title,msg,sig.grade,CFG["alerts"].get("enable_browser_notification",True))
    if html: components.html(html,height=0)
    st.toast(f"{title}：{msg}")
    state.update(last_alert_ts=now,last_alert_grade=sig.grade,last_alert_side=sig.side,last_alert_key=sig.key_level)
    save_state(state)

st.caption("盘口为实时快照；新闻风险模块是标题关键词启发式过滤，不等同于人工核实。所有交易需手动确认。")

if auto:
    time.sleep(CFG["app"]["refresh_seconds"])
    st.rerun()
