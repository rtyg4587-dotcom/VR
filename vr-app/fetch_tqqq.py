#!/usr/bin/env python3
"""TQQQ 종가를 tqqq.json에 기록 (GitHub Actions에서 실행)
1차: chart API 직접 호출 → 403 시 2차: 쿠키+crumb 인증 후 quote API
"""
import json, urllib.request, http.cookiejar, datetime, sys

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

def write_out(close, prev, date):
    out = {"ticker": "TQQQ", "close": round(close, 2),
           "prevClose": round(prev, 2) if prev else None, "date": date,
           "updated": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}
    with open("tqqq.json", "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("OK", out)

def try_chart():
    url = "https://query1.finance.yahoo.com/v8/finance/chart/TQQQ?range=5d&interval=1d"
    data = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20))
    res = data["chart"]["result"][0]
    pairs = [(t, c) for t, c in zip(res["timestamp"], res["indicators"]["quote"][0]["close"]) if c is not None]
    t, close = pairs[-1]
    prev = pairs[-2][1] if len(pairs) > 1 else None
    write_out(close, prev, datetime.datetime.utcfromtimestamp(t).strftime("%Y-%m-%d"))

def try_crumb():
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.addheaders = list(UA.items())
    try:
        op.open("https://fc.yahoo.com", timeout=20)
    except Exception:
        pass  # 쿠키만 획득
    crumb = op.open("https://query1.finance.yahoo.com/v1/test/getcrumb", timeout=20).read().decode()
    url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols=TQQQ&crumb={crumb}"
    q = json.load(op.open(url, timeout=20))["quoteResponse"]["result"][0]
    write_out(q["regularMarketPrice"], q.get("regularMarketPreviousClose"),
              datetime.datetime.utcfromtimestamp(q["regularMarketTime"]).strftime("%Y-%m-%d"))

try:
    try_chart()
except Exception as e1:
    print("chart API 실패, crumb 폴백 시도:", e1, file=sys.stderr)
    try:
        try_crumb()
    except Exception as e2:
        print("FETCH FAILED:", e2, file=sys.stderr)
        sys.exit(0)  # 실패해도 기존 tqqq.json 유지
