from __future__ import annotations
import requests, pandas as pd
from urllib.request import getproxies

BASE="https://fapi.binance.com"

class BinancePublicData:
    def __init__(self, timeout=15, use_windows_system_proxy=True, custom_proxy=""):
        self.timeout=timeout
        self.s=requests.Session()
        self.s.headers.update({"User-Agent":"ETHUSDT-AA-Monitor/1.4"})
        self.proxy_info="DIRECT"

        proxies={}
        if custom_proxy:
            proxies={"http":custom_proxy,"https":custom_proxy}
            self.proxy_info=f"CUSTOM {custom_proxy}"
        elif use_windows_system_proxy:
            try:
                p=getproxies() or {}
                http_p=p.get("http")
                https_p=p.get("https") or http_p
                if http_p or https_p:
                    proxies={}
                    if http_p: proxies["http"]=http_p
                    if https_p: proxies["https"]=https_p
                    self.proxy_info=f"SYSTEM {proxies}"
            except Exception:
                pass
        if proxies:
            self.s.proxies.update(proxies)

    def _get(self,path,params=None):
        r=self.s.get(BASE+path,params=params or {},timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def ping(self):
        return self._get("/fapi/v1/ping")

    def klines(self,symbol,interval,limit=500):
        raw=self._get("/fapi/v1/klines",{"symbol":symbol,"interval":interval,"limit":limit})
        cols=["open_time","open","high","low","close","volume","close_time","quote_volume","trades","taker_buy_base","taker_buy_quote","ignore"]
        df=pd.DataFrame(raw,columns=cols)
        for c in ["open","high","low","close","volume","quote_volume","taker_buy_base","taker_buy_quote"]:
            df[c]=pd.to_numeric(df[c],errors="coerce")
        df["open_time"]=pd.to_datetime(df["open_time"],unit="ms",utc=True)
        df["close_time"]=pd.to_datetime(df["close_time"],unit="ms",utc=True)
        return df
    def mark_price(self,symbol):
        return self._get("/fapi/v1/premiumIndex",{"symbol":symbol})
    def funding_history(self,symbol,limit=30):
        df=pd.DataFrame(self._get("/fapi/v1/fundingRate",{"symbol":symbol,"limit":limit}))
        if len(df):
            df["fundingRate"]=pd.to_numeric(df["fundingRate"],errors="coerce")
            df["fundingTime"]=pd.to_datetime(df["fundingTime"],unit="ms",utc=True)
        return df
    def open_interest_hist(self,symbol,period="1h",limit=100):
        df=pd.DataFrame(self._get("/futures/data/openInterestHist",{"symbol":symbol,"period":period,"limit":limit}))
        if len(df):
            for c in ["sumOpenInterest","sumOpenInterestValue"]:
                df[c]=pd.to_numeric(df[c],errors="coerce")
            df["timestamp"]=pd.to_datetime(df["timestamp"],unit="ms",utc=True)
        return df
    def _ratio(self,path,symbol,period="1h",limit=100):
        df=pd.DataFrame(self._get(path,{"symbol":symbol,"period":period,"limit":limit}))
        if len(df):
            for c in ["longShortRatio","longAccount","shortAccount"]:
                if c in df.columns: df[c]=pd.to_numeric(df[c],errors="coerce")
            df["timestamp"]=pd.to_datetime(df["timestamp"],unit="ms",utc=True)
        return df
    def global_long_short(self,symbol,period="1h",limit=100):
        return self._ratio("/futures/data/globalLongShortAccountRatio",symbol,period,limit)
    def top_account_long_short(self,symbol,period="1h",limit=100):
        return self._ratio("/futures/data/topLongShortAccountRatio",symbol,period,limit)
    def top_position_long_short(self,symbol,period="1h",limit=100):
        return self._ratio("/futures/data/topLongShortPositionRatio",symbol,period,limit)
    def taker_buy_sell(self,symbol,period="1h",limit=100):
        df=pd.DataFrame(self._get("/futures/data/takerlongshortRatio",{"symbol":symbol,"period":period,"limit":limit}))
        if len(df):
            for c in ["buySellRatio","buyVol","sellVol"]:
                df[c]=pd.to_numeric(df[c],errors="coerce")
            df["timestamp"]=pd.to_datetime(df["timestamp"],unit="ms",utc=True)
        return df
    def order_book(self,symbol,limit=500):
        return self._get("/fapi/v1/depth",{"symbol":symbol,"limit":limit})
