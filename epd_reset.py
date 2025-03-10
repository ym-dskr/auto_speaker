import display.epd7in5_V2 as epd7in5_V2

epd = epd7in5_V2.EPD()  # 電子ペーパーの初期化
epd.init()

# 画面をクリア
epd.Clear()

epd.sleep()
