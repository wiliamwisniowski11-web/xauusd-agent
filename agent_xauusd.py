import anthropic
import requests
import schedule
import time
import os
from datetime import datetime

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
TWELVE_DATA_KEY = os.environ.get("TWELVE_DATA_KEY")

def get_gold_data(interval, size):
    try:
        url = "https://api.twelvedata.com/time_series?symbol=XAU/USD&interval=" + interval + "&outputsize=" + str(size) + "&apikey=" + TWELVE_DATA_KEY
        r = requests.get(url, timeout=10).json()
        if "values" in r:
            return r["values"]
        return None
    except Exception as e:
        print("Erreur donnees : " + str(e))
        return None

def send_telegram(message):
    try:
        url = "https://api.telegram.org/bot" + TELEGRAM_TOKEN + "/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=10)
        print("Message Telegram envoye !")
    except Exception as e:
        print("Erreur Telegram : " + str(e))

def run_analysis():
    print("Analyse XAUUSD multi-timeframe en cours...")
    try:
        daily = get_gold_data("1day", 10)
        h4 = get_gold_data("4h", 20)
        h1 = get_gold_data("1h", 50)

        prix_actuel = h1[0]["close"] if h1 else "inconnu"
        print("Prix actuel : " + prix_actuel)

        daily_str = str(daily[:5]) if daily else "indisponible"
        h4_str = str(h4[:10]) if h4 else "indisponible"
        h1_str = str(h1[:10]) if h1 else "indisponible"

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1500,
            system="Tu es un expert trading XAUUSD specialise Smart Money Concepts. Tu fais une analyse top-down. Reponds en francais. Tu dois produire DEUX blocs separes par ---DETAIL---. Le premier bloc est un resume court avec : direction, entree, SL, TP1, TP2, RR et PROBABILITE XX%. Le deuxieme bloc est l'analyse complete detaillee.",
            messages=[{"role": "user", "content": "Prix actuel XAUUSD : " + prix_actuel + "\n\nDAILY : " + daily_str + "\n\n4H : " + h4_str + "\n\n1H : " + h1_str + "\n\nProduis les deux blocs demandes."}]
        )

        analyse = message.content[0].text
        now = datetime.now().strftime("%d/%m/%Y a %H:%M")

        if "---DETAIL---" in analyse:
            parties = analyse.split("---DETAIL---")
            resume = parties[0].strip()
            detail = parties[1].strip()
            msg1 = "XAUUSD - " + now + "\nPrix : " + prix_actuel + "\n\n" + resume
            msg2 = "ANALYSE COMPLETE :\n\n" + detail
            send_telegram(msg1)
            time.sleep(2)
            send_telegram(msg2)
        else:
            msg = "XAUUSD - " + now + "\nPrix : " + prix_actuel + "\n\n" + analyse
            send_telegram(msg)

    except Exception as e:
        print("Erreur : " + str(e))

def check_telegram_commands():
    try:
        url = "https://api.telegram.org/bot" + TELEGRAM_TOKEN + "/getUpdates?offset=-1"
        r = requests.get(url, timeout=10).json()
        if r["result"]:
            last = r["result"][-1]
            update_id = last["update_id"]
            if "message" in last:
                text = last["message"].get("text", "")
                msg_time = last["message"]["date"]
                now_time = int(time.time())
                if text == "/analyse" and now_time - msg_time < 60:
                    print("Commande /analyse recue !")
                    requests.get("https://api.telegram.org/bot" + TELEGRAM_TOKEN + "/getUpdates?offset=" + str(update_id + 1))
                    run_analysis()
    except Exception as e:
        print("Erreur commande : " + str(e))

print("Agent XAUUSD demarre !")
print("Commandes : /analyse")
run_analysis()
schedule.every().hour.at(":00").do(run_analysis)

while True:
    schedule.run_pending()
    check_telegram_commands()
    time.sleep(10)