[app]
title = TradeBot
package.name = tradebot
package.domain = org.tradebot
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 0.5

# نسخه‌های پین‌شده که با بیلد ابری بهتر جواب می‌دهند
requirements = python3,kivy==2.3.0,telethon==1.35.0,requests==2.32.3

orientation = portrait
fullscreen = 0

# ---- Android ----
android.api = 31
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True
android.archs = arm64-v8a, armeabi-v7a
p4a.branch = stable

# در صورت نیاز به دسترسی‌های بیشتر اینجا اضافه کن
# android.permissions = INTERNET
