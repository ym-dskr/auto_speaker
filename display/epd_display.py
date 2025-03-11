import sys
sys.path.append('/home/yutapi/scripts')
from auto_speaker.display import epd7in5_V2  # 使っている電子ペーパーのライブラリ
from PIL import Image, ImageDraw, ImageFont
import time
from PIL import Image, ImageDraw, ImageFont

def wrap_text(text, font, max_width, draw):
    """
    指定された幅に収まるように1文字ずつチェックしながらテキストを折り返す（ピクセル単位）。
    """
    lines = []
    current_line = ""
    
    for char in text:  # 日本語は単語ではなく文字単位で処理
        test_line = current_line + char
        bbox = draw.textbbox((0, 0), test_line, font=font)  # 幅を取得
        line_width = bbox[2] - bbox[0]  # x2 - x1 で幅を計算

        if line_width <= max_width:
            current_line = test_line  # 幅内ならそのまま追加
        else:
            lines.append(current_line)  # 幅を超えたら折り返し
            current_line = char  # 新しい行を開始

    if current_line:  # 最後の行を追加
        lines.append(current_line)

    return lines

def display_text(text):
    """
    電子ペーパーにテキストを表示する（ピクセル単位で折り返し）
    """
    epd = epd7in5_V2.EPD()  # 電子ペーパーの初期化
    epd.init()

    # 画面をクリア
    epd.Clear()

    # 画像作成（白背景）
    image = Image.new('1', (epd.width, epd.height), 255)
    draw = ImageDraw.Draw(image)

    # フォント設定（日本語対応フォント）
    font_path = "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf"
    font_size = 24  # フォントサイズ
    font = ImageFont.truetype(font_path, font_size)

    # 折り返し処理（ピクセル単位）
    max_width = epd.width - 40  # 左右に10pxずつ余白
    wrapped_lines = wrap_text(text, font, max_width, draw)

    # フォントの高さを取得（「あ」の高さを基準にする）
    _, _, _, line_height = draw.textbbox((0, 0), "あ", font=font)  
    line_spacing = line_height + 5  # 適切な行間

    # テキストを描画
    y_position = 10

    for line in wrapped_lines:
        bbox = draw.textbbox((0, 0), line, font=font)  # 行の高さを取得
        actual_line_height = bbox[3] - bbox[1]  # y2 - y1 で高さを計算

        draw.text((24, y_position), line, font=font, fill=0)
        y_position += actual_line_height + 5  # 行の高さ+余白を適用

        # 画面からはみ出したら途中で終了
        if y_position > epd.height - actual_line_height:
            break

    # 画像を電子ペーパーに転送
    epd.display(epd.getbuffer(image))
    epd.sleep()

    print("電子ペーパーに表示しました！")

def display_image(image):
    """
    電子ペーパーに画像を表示
    """
    # 電子ペーパーのサイズ
    EPD_WIDTH = 800
    EPD_HEIGHT = 480
    
    # 画像サイズを確認
    if image.size != (EPD_WIDTH, EPD_HEIGHT):
        print(f"警告: 画像サイズが正しくありません。現在: {image.size}, 必要: {EPD_WIDTH}x{EPD_HEIGHT}")
        print("画像を正確なサイズにリサイズします。")
        try:
            from PIL.Image import Resampling
            image = image.resize((EPD_WIDTH, EPD_HEIGHT), Resampling.LANCZOS)
        except (ImportError, AttributeError):
            image = image.resize((EPD_WIDTH, EPD_HEIGHT), Image.LANCZOS)
    
    epd = epd7in5_V2.EPD()
    epd.init()

    # 画像をグレースケール変換 & 1bit変換（電子ペーパー用）
    image = image.convert("L").convert("1")  

    # 画像サイズの最終確認
    if image.size != (EPD_WIDTH, EPD_HEIGHT):
        raise ValueError(f"Wrong image dimensions: must be {EPD_WIDTH}x{EPD_HEIGHT}")

    # 画像を電子ペーパーに表示
    epd.display(epd.getbuffer(image))
    epd.sleep()
    
    print("画像を電子ペーパーに表示しました！")

if __name__ == "__main__":
    display_text("こんにちは、電子ペーパー！")
