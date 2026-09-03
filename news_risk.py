from dataclasses import dataclass
from urllib.parse import quote_plus
import feedparser

@dataclass
class NewsRisk:
    level:str
    reason:str
    headlines:list[str]

def assess_news_risk(cfg):
    manual=str(cfg.get("manual_event_risk","auto")).lower()
    mp={"normal":"正常","elevated":"升高","升高":"升高","shock":"冲击","冲击":"冲击"}
    if manual in mp: return NewsRisk(mp[manual],"手动事件风险设置",[])
    if not cfg.get("enabled",True): return NewsRisk("正常","新闻风险过滤已关闭",[])
    q=cfg.get("google_news_rss_query","").strip()
    if not q: return NewsRisk("正常","未配置新闻源",[])
    try:
        url=f"https://news.google.com/rss/search?q={quote_plus(q)}&hl=en-US&gl=US&ceid=US:en"
        feed=feedparser.parse(url)
        titles=[e.get("title","") for e in feed.entries[:20]]
        text=" ".join(titles).lower()
        shock=[k for k in cfg.get("shock_keywords",[]) if k.lower() in text]
        high=[k for k in cfg.get("high_risk_keywords",[]) if k.lower() in text]
        if shock: return NewsRisk("冲击","命中高冲击新闻词："+", ".join(shock[:4]),titles[:8])
        if high: return NewsRisk("升高","命中事件风险词："+", ".join(high[:5]),titles[:8])
        return NewsRisk("正常","未发现明显突发风险关键词",titles[:8])
    except Exception as e:
        return NewsRisk("正常",f"新闻源读取失败，不做事件加分：{e}",[])
