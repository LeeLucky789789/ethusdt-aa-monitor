from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Optional
import numpy as np
import pandas as pd

@dataclass
class Signal:
    grade:str; score:int; side:str; price:float
    entry_low:float; entry_high:float; stop:float
    tp1:float; tp2:float; tp3:Optional[float]; rr:float
    hard_conditions_ok:bool; trend_4h:str; trend_1h:str
    trigger_15m:str; key_level:str
    event_risk:str; event_reason:str
    volume_state:str; taker_state:str; oi_state:str; funding_state:str
    crowd_state:str; top_trader_state:str; orderbook_state:str
    notes:list[str]; missing_for_upgrade:list[str]; do_not_chase:bool
    risk_rmb:float; notional_rmb:float; margin_rmb:float; qty_eth:float
    expected_loss_rmb:float; expected_profit_tp1_rmb:float
    expected_profit_tp2_rmb:float; expected_profit_tp3_rmb:Optional[float]
    def to_dict(self): return asdict(self)

def ema(s,n): return s.ewm(span=n,adjust=False).mean()

def atr(df,n=14):
    pc=df["close"].shift(1)
    tr=pd.concat([(df["high"]-df["low"]).abs(),
                  (df["high"]-pc).abs(),
                  (df["low"]-pc).abs()],axis=1).max(axis=1)
    return tr.rolling(n).mean()

def trend_state(df):
    c=df["close"]; e20,e50=ema(c,20),ema(c,50)
    slope=e20.iloc[-1]-e20.iloc[-6]
    if c.iloc[-1]>e20.iloc[-1]>e50.iloc[-1] and slope>0: return "BULL"
    if c.iloc[-1]<e20.iloc[-1]<e50.iloc[-1] and slope<0: return "BEAR"
    return "MIXED"

def volume_state(df):
    v=df["volume"]; base=v.tail(40).iloc[:-1].median()
    ratio=float(v.iloc[-1]/base) if base and np.isfinite(base) else 1.0
    if ratio>=1.5: return "强放量",ratio
    if ratio>=1.2: return "放量",ratio
    if ratio<=0.75: return "缩量",ratio
    return "正常",ratio

def compute_orderbook_state(book,price,band_pct=0.005):
    try:
        bids=[(float(p),float(q)) for p,q in book["bids"]]
        asks=[(float(p),float(q)) for p,q in book["asks"]]
        lo,hi=price*(1-band_pct),price*(1+band_pct)
        b=sum(p*q for p,q in bids if p>=lo); a=sum(p*q for p,q in asks if p<=hi)
        ratio=b/a if a>0 else np.inf
        if ratio>=1.25: state="买盘占优"
        elif ratio<=0.80: state="卖盘占优"
        else: state="中性"
        return state,ratio
    except Exception:
        return "数据不足",np.nan

def pct_change_latest(df,col):
    if df is None or len(df)<2: return np.nan
    a,b=float(df[col].iloc[-2]),float(df[col].iloc[-1])
    return np.nan if a==0 else b/a-1

def choose_side_and_trigger(df15,df1h,df4h):
    t4,t1=trend_state(df4h),trend_state(df1h)
    ph=float(df15["high"].iloc[-21:-1].max())
    pl=float(df15["low"].iloc[-21:-1].min())
    c,o=float(df15["close"].iloc[-1]),float(df15["open"].iloc[-1])
    if t4=="BULL" and t1 in {"BULL","MIXED"}:
        side="LONG"
        trigger="15m突破近20根高点" if c>ph else ("15m多头实体确认" if c>o else "等待15m确认")
        key=f"近20根15m阻力 {ph:.2f}"
    elif t4=="BEAR" and t1 in {"BEAR","MIXED"}:
        side="SHORT"
        trigger="15m跌破近20根低点" if c<pl else ("15m空头实体确认" if c<o else "等待15m确认")
        key=f"近20根15m支撑 {pl:.2f}"
    else:
        side="LONG" if t1=="BULL" else "SHORT"
        trigger="多周期未对齐"; key="无明确硬条件"
    return side,trigger,key,t4,t1

def build_trade_plan(side,price,df1h):
    a=float(atr(df1h,14).iloc[-1])
    if not np.isfinite(a) or a<=0: a=price*0.012
    if side=="LONG":
        entry_low,entry_high=price-.20*a,price+.10*a
        stop=price-1.15*a
        tp1,tp2,tp3=price+1.75*a,price+2.60*a,price+3.50*a
        rr=(tp2-price)/(price-stop)
    else:
        entry_low,entry_high=price-.10*a,price+.20*a
        stop=price+1.15*a
        tp1,tp2,tp3=price-1.75*a,price-2.60*a,price-3.50*a
        rr=(price-tp2)/(stop-price)
    return entry_low,entry_high,stop,tp1,tp2,tp3,rr,a

def evaluate(data,cfg,event_risk="正常",event_reason=""):
    df15,df1h,df4h=data["15m"],data["1h"],data["4h"]
    price=float(df15["close"].iloc[-1])
    side,trigger,key,t4,t1=choose_side_and_trigger(df15,df1h,df4h)
    entry_low,entry_high,stop,tp1,tp2,tp3,rr,a1h=build_trade_plan(side,price,df1h)
    score=0; notes=[]; missing=[]; hard=True

    # Trend / structure: 25
    if (side=="LONG" and t4=="BULL" and t1=="BULL") or (side=="SHORT" and t4=="BEAR" and t1=="BEAR"):
        score+=25; notes.append("4h/1h 同向")
    elif (side=="LONG" and t4=="BULL" and t1=="MIXED") or (side=="SHORT" and t4=="BEAR" and t1=="MIXED"):
        score+=18; missing.append("1h进一步同向")
    else:
        score+=7; hard=False; missing.append("4h/1h方向对齐")

    # Key/trigger: 20
    trig_ok=("突破" in trigger or "跌破" in trigger)
    if trig_ok:
        score+=20; notes.append(trigger)
    elif "实体确认" in trigger:
        score+=12; hard=False; missing.append("关键位突破/跌破或回踩确认")
    else:
        score+=3; hard=False; missing.append("15m实际触发")

    # Volume + taker: 15
    vstate,vr=volume_state(df15)
    taker=data.get("taker")
    tratio=float(taker["buySellRatio"].iloc[-1]) if taker is not None and len(taker) else np.nan
    if side=="LONG":
        tgood=np.isfinite(tratio) and tratio>=1.06
        tstate=f"买方主动占优 {tratio:.2f}" if tgood else (f"买卖比 {tratio:.2f}" if np.isfinite(tratio) else "数据不足")
    else:
        tgood=np.isfinite(tratio) and tratio<=0.94
        tstate=f"卖方主动占优 {tratio:.2f}" if tgood else (f"买卖比 {tratio:.2f}" if np.isfinite(tratio) else "数据不足")
    score+=(8 if vr>=1.2 else 4)+(7 if tgood else 2)
    if vr>=1.2: notes.append(f"{vstate} {vr:.2f}×")
    if tgood: notes.append(tstate)

    # OI / funding: 10
    oi=data.get("oi"); oic=pct_change_latest(oi,"sumOpenInterestValue")
    oi_state="OI上升" if np.isfinite(oic) and oic>.002 else ("OI下降" if np.isfinite(oic) and oic<-.002 else "OI平稳/数据不足")
    funding=data.get("funding")
    fr=float(funding["fundingRate"].iloc[-1]) if funding is not None and len(funding) else np.nan
    funding_state=f"{fr*100:.4f}%" if np.isfinite(fr) else "数据不足"
    funding_penalty=(side=="LONG" and np.isfinite(fr) and fr>.0005) or (side=="SHORT" and np.isfinite(fr) and fr<-.0005)
    score+=(6 if np.isfinite(oic) and oic>0 else 3)+(1 if funding_penalty else 4)

    # Positioning / crowd: 10
    gls=data.get("global_ls"); tls=data.get("top_pos_ls")
    gr=float(gls["longShortRatio"].iloc[-1]) if gls is not None and len(gls) else np.nan
    top=float(tls["longShortRatio"].iloc[-1]) if tls is not None and len(tls) else np.nan
    crowd_state=f"全市场L/S={gr:.2f}" if np.isfinite(gr) else "全市场多空比数据不足"
    top_state=f"大户持仓L/S={top:.2f}" if np.isfinite(top) else "大户持仓多空比数据不足"
    cbonus=5
    if side=="SHORT" and np.isfinite(gr) and gr>=2.6:
        cbonus=7; notes.append("散户多头拥挤，存在下行清算燃料")
    elif side=="LONG" and np.isfinite(gr) and gr<=.65:
        cbonus=7; notes.append("散户空头拥挤，存在上行挤压燃料")
    elif side=="LONG" and np.isfinite(gr) and gr>=2.8:
        cbonus=2; missing.append("多头拥挤风险下降")
    elif side=="SHORT" and np.isfinite(gr) and gr<=.55:
        cbonus=2; missing.append("空头拥挤风险下降")
    tbonus=3
    if np.isfinite(top):
        ch=pct_change_latest(tls,"longShortRatio")
        if (side=="LONG" and np.isfinite(ch) and ch>0) or (side=="SHORT" and np.isfinite(ch) and ch<0): tbonus=3
        else: tbonus=1
    score+=min(10,cbonus+tbonus)

    # Orderbook: 5
    ob_state,ob_ratio=compute_orderbook_state(data.get("orderbook",{}),price,cfg["strategy"].get("orderbook_band_pct",.005))
    if (side=="LONG" and ob_state=="买盘占优") or (side=="SHORT" and ob_state=="卖盘占优"):
        score+=5; notes.append("近价盘口与方向一致")
    else: score+=2

    # R:R & target space: 10
    target_pct=abs(tp1-price)/price
    min_target=cfg["strategy"]["min_target_pct"]
    if rr>=cfg["strategy"]["min_rr_Aplus"] and target_pct>=min_target: score+=10
    elif rr>=cfg["strategy"]["min_rr_A"] and target_pct>=min_target: score+=8
    else:
        score+=2; hard=False
        if rr<cfg["strategy"]["min_rr_A"]: missing.append("R:R ≥ 2.0")
        if target_pct<min_target: missing.append("目标空间覆盖成本与噪声")

    # Event / execute: 5
    if event_risk=="正常": score+=5
    elif event_risk=="升高":
        score-=7; missing.append("事件风险回落")
    else:
        score-=20; hard=False; missing.append("等待事件冲击稳定")

    score=int(max(0,min(100,score)))
    if not hard: grade="B" if score>=60 else "C"
    elif score>=cfg["strategy"]["score_Aplus"] and rr>=cfg["strategy"]["min_rr_Aplus"]: grade="A+"
    elif score>=cfg["strategy"]["score_A"] and rr>=cfg["strategy"]["min_rr_A"]: grade="A"
    elif score>=60: grade="B"
    else: grade="C"

    midpoint=(entry_low+entry_high)/2
    do_not_chase=abs(price-midpoint)>.6*a1h

    equity=cfg["account"]["equity_rmb"]; lev=cfg["account"]["leverage"]
    risk_pct=cfg["account"]["risk_Aplus_pct"] if grade=="A+" else cfg["account"]["risk_A_pct"]
    if event_risk=="升高": risk_pct*=.5
    if grade not in {"A","A+"}: risk_pct=0
    risk_rmb=equity*risk_pct
    stop_pct=abs(stop-price)/price
    risk_notional=risk_rmb/stop_pct if stop_pct>0 else 0
    notional=min(risk_notional,equity*lev)
    margin=notional/lev if lev else 0
    fx=cfg["account"]["rmb_per_usdt"]
    qty=(notional/fx)/price if price else 0
    exp_loss=qty*abs(stop-price)*fx
    prof=lambda tp: qty*abs(tp-price)*fx

    return Signal(
        grade,score,side,price,entry_low,entry_high,stop,tp1,tp2,tp3,rr,hard,t4,t1,trigger,key,
        event_risk,event_reason,vstate,tstate,oi_state,funding_state,crowd_state,top_state,ob_state,
        notes,missing,do_not_chase,risk_rmb,notional,margin,qty,exp_loss,prof(tp1),prof(tp2),prof(tp3)
    )
