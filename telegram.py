"""Telegram notifier. Owner only. PAPER pushes start with 'PAPER · '."""

import os
import httpx

TG_TOKEN = os.environ.get("TG_TOKEN", "")
OWNER_CHAT = os.environ.get("TG_CHAT_ID", "6088938176")


async def send(text: str, button_url: str = None, button_label: str = "Buy on FOMO"):
    if not TG_TOKEN:
        print("Notifier: no TG_TOKEN, would have sent:", text[:80])
        return
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {
        "chat_id": OWNER_CHAT,
        "text": text,
        "parse_mode": "HTML",
    }
    if button_url:
        payload["reply_markup"] = {
            "inline_keyboard": [[{"text": button_label, "url": button_url}]]
        }
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.post(url, json=payload)
            if r.status_code == 200:
                print("Notifier: push sent")
            else:
                print("Notifier error:", r.status_code, r.text[:100])
        except Exception as e:
            print("Notifier exception:", e)
