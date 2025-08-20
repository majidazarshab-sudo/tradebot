from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
import threading, json, re, time, hmac, hashlib, requests, os
from urllib.parse import urlencode
from telethon import TelegramClient, events

CONFIG_FILE = "config.json"
LOG_FILE = "tradelog.json"

# ================== UI ==================
class ConfigScreen(BoxLayout):
    def __init__(self, start_callback, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"

        self.api_id_input = TextInput(hint_text="Telegram API ID", multiline=False)
        self.api_hash_input = TextInput(hint_text="Telegram API Hash", multiline=False)
        self.channel_input = TextInput(hint_text="Telegram Channel Username", multiline=False)
        self.lbank_key_input = TextInput(hint_text="LBank API Key", multiline=False)
        self.lbank_secret_input = TextInput(hint_text="LBank API Secret", multiline=False, password=True)

        self.add_widget(self.api_id_input)
        self.add_widget(self.api_hash_input)
        self.add_widget(self.channel_input)
        self.add_widget(self.lbank_key_input)
        self.add_widget(self.lbank_secret_input)

        self.start_btn = Button(text="Start Bot")
        self.start_btn.bind(on_press=lambda x: start_callback(
            self.api_id_input.text,
            self.api_hash_input.text,
            self.channel_input.text,
            self.lbank_key_input.text,
            self.lbank_secret_input.text
        ))
        self.add_widget(self.start_btn)

class TradeBot(BoxLayout):
    def __init__(self, api_key, api_secret, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.log = Label(text="ربات آماده است...", halign="left", valign="top")
        self.add_widget(self.log)

        # دکمه نمایش تاریخچه
        self.history_btn = Button(text="📜 نمایش تاریخچه معاملات")
        self.history_btn.bind(on_press=lambda x: self.show_history())
        self.add_widget(self.history_btn)

        threading.Thread(target=self.update_positions, args=(api_key, api_secret), daemon=True).start()

    def add_log(self, msg):
        self.log.text += f"\n{msg}"

    def update_positions(self, api_key, api_secret):
        while True:
            try:
                positions = get_open_positions(api_key, api_secret)
                self.log.text += f"\n📊 پوزیشن‌های باز: {positions}"
            except Exception as e:
                self.log.text += f"\n❌ خطا در دریافت پوزیشن‌ها: {e}"
            time.sleep(20)

    def show_history(self):
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                logs = f.read()
            self.log.text += f"\n===== تاریخچه معاملات =====\n{logs}"
        else:
            self.log.text += "\n📭 هیچ تاریخچه‌ای وجود ندارد."

# ================== لاگ ==================
def save_log(entry):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

# ================== API توابع ==================
def sign_payload(payload, secret):
    query = urlencode(payload)
    signature = hmac.new(secret.encode(), query.encode(), hashlib.sha256).hexdigest()
    return signature

def lbank_request(endpoint, payload, api_key, api_secret):
    payload["api_key"] = api_key
    payload["timestamp"] = int(time.time() * 1000)
    payload["sign"] = sign_payload(payload, api_secret)
    url = f"https://api.lbkex.com{endpoint}"
    r = requests.post(url, data=payload)
    return r.json()

def place_futures_order(symbol, side, size, leverage, entry, sl, tps, api_key, api_secret):
    payload = {
        "symbol": symbol,
        "type": "market",
        "side": side,
        "size": size,
        "open_type": "isolated",
        "leverage": leverage,
        "position_id": 0,
    }
    res = lbank_request("/v2/futures/order", payload, api_key, api_secret)

    log_entry = {"symbol": symbol, "side": side, "entry": entry, "sl": sl, "tps": tps, "result": res}
    save_log(log_entry)

    if res.get("result", True):
        for tp in tps:
            if tp:
                tp_payload = {
                    "symbol": symbol,
                    "side": "sell" if side == "buy" else "buy",
                    "size": size/len(tps),
                    "type": "take_profit",
                    "stop_price": tp,
                    "leverage": leverage,
                    "open_type": "isolated"
                }
                lbank_request("/v2/futures/order", tp_payload, api_key, api_secret)
        if sl:
            sl_payload = {
                "symbol": symbol,
                "side": "sell" if side == "buy" else "buy",
                "size": size,
                "type": "stop",
                "stop_price": sl,
                "leverage": leverage,
                "open_type": "isolated"
            }
            lbank_request("/v2/futures/order", sl_payload, api_key, api_secret)
    return res

def get_open_positions(api_key, api_secret):
    payload = {}
    res = lbank_request("/v2/futures/positions", payload, api_key, api_secret)
    return res

# ================== ربات تلگرام ==================
def run_telegram(bot_ui, api_id, api_hash, channel, api_key, api_secret):
    client = TelegramClient("session", int(api_id), api_hash)

    @client.on(events.NewMessage(chats=channel))
    async def handler(event):
        text = event.message.message
        bot_ui.add_log("سیگنال جدید: " + text)

        side = "buy" if "LONG" in text.upper() else "sell"
        entry = re.findall(r"Enter price:\s*([\d\.]+)", text)
        tp1 = re.findall(r"TP1:\s*([\d\.]+)", text)
        tp2 = re.findall(r"TP2:\s*([\d\.]+)", text)
        tp3 = re.findall(r"TP3:\s*([\d\.]+)", text)
        sl = re.findall(r"Stop Loss:\s*([\d\.]+)", text)

        if entry and sl and (tp1 or tp2 or tp3):
            entry = float(entry[0])
            tps = []
            if tp1: tps.append(float(tp1[0]))
            if tp2: tps.append(float(tp2[0]))
            if tp3: tps.append(float(tp3[0]))
            sl = float(sl[0])

            res = place_futures_order("sol_usdt", side, 0.3, 12, entry, sl, tps, api_key, api_secret)
            bot_ui.add_log(f"سفارش ارسال شد: {res}")

    client.start()
    client.run_until_disconnected()

# ================== اپ ==================
class TradeApp(App):
    def build(self):
        return ConfigScreen(self.start_bot)

    def start_bot(self, api_id, api_hash, channel, lbank_key, lbank_secret):
        config = {
            "api_id": api_id,
            "api_hash": api_hash,
            "channel": channel,
            "lbank_key": lbank_key,
            "lbank_secret": lbank_secret
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f)

        self.root.clear_widgets()
        ui = TradeBot(lbank_key, lbank_secret)
        self.root.add_widget(ui)

        threading.Thread(target=run_telegram, args=(ui, api_id, api_hash, channel, lbank_key, lbank_secret), daemon=True).start()

if __name__ == "__main__":
    TradeApp().run()
