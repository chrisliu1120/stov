from flask import Flask, request
import time
import requests
from linebot.v3.messaging import MessagingApi, ReplyMessageRequest, TextMessage, Configuration, ApiClient
from dotenv import load_dotenv
import os



app = Flask(__name__)


# 載入 .env 檔案
load_dotenv()
CaT = os.getenv("CaT")
Channel_secret = os.getenv("Channel_secret")

configuration = Configuration(access_token=CaT)


# 查詢股價進入點
def stockprice(stock_codes):
    codeno = f'tse_{stock_codes}.tw'
    timestamp = int(time.time() * 1000)
    api_url = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch={codeno}&_={timestamp}"
    rate = requests.get(api_url)
    req = rate.json()
    stock_data = req['msgArray']

    # --- 取值邏輯 ---
    code = stock_data[0].get('c')
    name = stock_data[0].get('n')
    price = stock_data[0].get('z', '-')
    bid_price = stock_data[0].get('b', '_').split('_')[0]
    yesterday_price = stock_data[0].get('y', '-')
    source = ""
    vol = stock_data[0].get('v', 'N/A')
    # --- 價格取值邏輯 ---
    if price == '-':
        if bid_price and bid_price != '-':
            price = bid_price
            source = "(委買)"
        elif yesterday_price and yesterday_price != '-':
            price = yesterday_price
            source = "(昨收)"
    price_int = price[0:-2]                 #prince值為字串，所以取到倒數兩位數
    # --- 漲跌計算邏輯 ---
    change = "N/A"
    percentage = "N/A"
    updown = "N/A"
    if yesterday_price != '-' and price != '-':
        change_val = float(price) - float(yesterday_price)
        if change_val > 0:
            updown = "▲"
        elif change_val < 0:
            updown = "▼"
        elif change_val == 0:
            updown = "--"

        percentage_val = (change_val / float(yesterday_price)) * 100
        change = f"{change_val:+.2f}"
        percentage = f"{percentage_val:+.2f}%"

    quotes = {}
    quotes = {
        '股票代碼': code,
        '公司簡稱': stock_data[0].get('n', 'N/A'),
        '成交價': price,
        '來源': source,
        '成交量': stock_data[0].get('v', 'N/A'),
            }
    text = f"{name}\n最新成交價:{price_int}{source}\n{updown}漲跌:{change}＊漲跌幅:{percentage}\n成交量:{vol}"
    return text

# 設定 LINE BOT Token
BOT_TOKEN = CaT

# 傳送文字訊息函數
def send_text_message(reply_token, text):
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + BOT_TOKEN
    }

    payload = {
        "replyToken": reply_token,
        "messages": [{
            "type": "text",
            "text": text
        },
        #{
            #"type": "sticker",
            #"packageId": "8525",
            #"stickerId": "16581291"
        #}
     ]
    }

    # 發送 POST 請求至 LINE Messaging API
    response = requests.post(
        "https://api.line.me/v2/bot/message/reply",
        headers=headers,
        json=payload
    )
    return response

# LINE Webhook 入口
@app.route("/linebot", methods=['POST'])
def linebot():
    # 取得使用者傳來的資料
    data = request.get_json()
    print(data)

    # 採用手動方式進行 X-Line-Signature 簽章驗證，確保訊息來源為 LINE 官方伺服器
    import hmac, hashlib, base64
    from flask import abort

    body = request.get_data(as_text=True)
    signature = request.headers.get("X-Line-Signature", "")
    hash = hmac.new(Channel_secret.encode(), body.encode(), hashlib.sha256).digest()
    if signature != base64.b64encode(hash).decode():
        abort(400)
    else:
        # 提取 replyToken
        reply_token = data['events'][0]['replyToken']

        # 提取 text(使用者輸入的股票代號)
        stock_codes = data["events"][0]["message"]["text"]
        print(stock_codes)

        # 執行查詢股價函式
        retext = stockprice(stock_codes)

        # 回傳文字訊息
        response = send_text_message(reply_token, retext)#使用上面的 def send_text_message(reply_token, text):
        if response.status_code == 200:
            return "OK", 200
        else:
            print("發送訊息失敗:", response.status_code, response.text)
            return "Error", 400



@app.route("/")
def index():
    return "<h1>你看不見我</h1>"

# 啟動 Flask 伺服器
if __name__ == "__main__":
    app.run(host="0.0.0.0",port=5001, debug=True)
