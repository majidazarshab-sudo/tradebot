[app]
title = TradeBot
package.name = tradebot
package.domain = org.tradebot
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 0.5
requirements = python3,kivy,telethon,requests
orientation = portrait
fullscreen = 0

[buildozer]
log_level = 2
warn_on_root = 1

[android]
android.permissions = INTERNET
