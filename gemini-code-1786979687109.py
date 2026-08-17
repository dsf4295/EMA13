import time
import requests
import pandas as pd

# --- 設定項目 ---
API_KEY = "ここにTwelve_DataのAPIキーを貼り付け"
SYMBOL = "USD/JPY"             # 監視したい通貨ペア（USD/JPYなど）
INTERVAL = "1min"              # スキャルピング用の足
NTFY_TOPIC = "my-fx-scalping-777" # Step1で決めたトピック名

# pipsの定義（USD/JPYなどのクロス円は 1pip = 0.01、EUR/USDなどは 1pip = 0.0001）
PIP_VALUE = 0.01 if "JPY" in SYMBOL else 0.0001

def send_ntfy(message):
    """iPhoneへ通知を送る関数"""
    url = f"https://ntfy.sh/{NTFY_TOPIC}"
    requests.post(url, data=message.encode('utf-8'))

def check_signal():
    """EMA100とEMA13を計算して判定する関数"""
    url = f"https://api.twelvedata.com/time_series?symbol={SYMBOL}&interval={INTERVAL}&outputsize=150&apikey={API_KEY}"
    res = requests.get(url).json()

    if "values" not in res:
        print("データ取得エラー:", res)
        return

    # データを解析用の形に変換
    df = pd.DataFrame(res["values"])
    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df = df.iloc[::-1].reset_index(drop=True)

    # EMA（指数移動平均線）を計算
    df["ema13"] = df["close"].ewm(span=13, adjust=False).mean()
    df["ema100"] = df["close"].ewm(span=100, adjust=False).mean()

    # 直近の2本の足を取得
    latest = df.iloc[-1]   # 最新の足
    prev = df.iloc[-2]     # 1つ前の足

    # --- 条件の計算 ---
    # 1. EMA100の差分（pips換算）
    ema100_diff = (latest["ema100"] - prev["ema100"]) / PIP_VALUE

    # 2. ローソク足がEMA13に接触したか？（安値 <= EMA13 <= 高値）
    is_touch_ema13 = (latest["low"] <= latest["ema13"]) and (latest["ema13"] <= latest["high"])

    # --- 判定と通知 ---
    # 【買い条件】EMA100が1pips以上「上昇」 ＋ EMA13にタッチ
    if ema100_diff >= 1.0 and is_touch_ema13:
        msg = f"【ロングチャンス】{SYMBOL} ({INTERVAL})\nEMA100が+{ema100_diff:.1f}pips上昇中！EMA13にタッチしました。"
        send_ntfy(msg)
        print("買い通知送信:", msg)

    # 【売り条件】EMA100が1pips以上「下降」 ＋ EMA13にタッチ
    elif ema100_diff <= -1.0 and is_touch_ema13:
        msg = f"【ショートチャンス】{SYMBOL} ({INTERVAL})\nEMA100が{ema100_diff:.1f}pips下降中！EMA13にタッチしました。"
        send_ntfy(msg)
        print("売り通知送信:", msg)

if __name__ == "__main__":
    send_ntfy("自動監視（1pips条件追加版）を開始しました！")
    while True:
        try:
            check_signal()
        except Exception as e:
            print("エラーが発生しました:", e)
        time.sleep(60) # 1分毎にチェック