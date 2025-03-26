import os
from dotenv import load_dotenv
import subprocess
from voice import get_voice
from api import chat, generate_image, chat_with_gpt, download_and_resize_image, save_image
from api import tts_voice
from display import epd_display
from camera import camera_control
from PIL import Image
import re
import sys
import simpleaudio as sa

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

def is_image_request(prompt):
    """
    ユーザーの入力が画像生成の指示かどうかを判定
    """
    keywords = ["絵を描いて",
                "イラストを作って", 
                "画像を生成",
                "写真を作成", 
                "描いて"]
    return any(keyword in prompt for keyword in keywords)

def check_for_camera_command(text):
    """
    テキスト内に「はいチーズ」や「はい、チーズ」のような写真撮影コマンドが含まれているか確認
    """
    # より柔軟な正規表現パターン（「チーズ」のカタカナ表記や濁音も許容）
    patterns = [
        r'はい.*チーズ',      # 「はい」の後に何か文字があって「チーズ」
        r'はい.*ちーず',      # ひらがな表記
        r'はい.*ティーズ',    # カタカナ混じり表記
        r'はい.*キーズ',
        r'はい.*cheese'           # ひらがな表記
    ]
    
    # テキストを小文字に変換（英語部分のため）
    text_lower = text.lower()
    
    # デバッグ出力
    print(f"コマンド検出: 入力テキスト「{text}」")
    
    # いずれかのパターンにマッチするか確認
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            print(f"マッチしたパターン: {pattern}")
            return True
        
    print("写真撮影コマンドは検出されませんでした")
    return False

if __name__ == "__main__":
    from api import tts_voice
    
    # 音声再生
    wave_obj = sa.WaveObject.from_wave_file("/home/yutapi/scripts/auto_speaker/sounds/start.wav")
    wave_obj.play().wait_done()
    
    try:
        # 音声録音 & Whisper でテキスト化
        audio_file = get_voice.record_audio()
        if audio_file is None:
            print("音声入力がタイムアウトしました。")
            # tts_voice.text_to_speech("何もないんかい、また来てな！")
            wave_obj = sa.WaveObject.from_wave_file("/home/yutapi/scripts/auto_speaker/sounds/no_request.wav")
            wave_obj.play().wait_done()
            
            subprocess.Popen(['/home/yutapi/myenv/bin/python3', '/home/yutapi/scripts/auto_speaker/ultra_sonic/distance.py'])
            sys.exit()
            
        text = get_voice.transcribe_audio()
        print("認識結果:", text)

        # 「はいチーズ」系のコマンドかどうかチェック
        if check_for_camera_command(text):
            print("写真撮影コマンドを検出しました！")
            # 写真を撮影
            photo_path, photo_image = camera_control.capture_photo()
            print(f"写真を保存しました: {photo_path}")
            # 撮影した写真を電子ペーパーに表示
            epd_display.display_image(photo_image)
            print("写真を電子ペーパーに表示しました")
        elif is_image_request(text):
            # 画像生成
            print("画像生成モード: DALL·E を使用")
            image_url = generate_image(text)
            image = download_and_resize_image(image_url)
            save_image(image, text)
            epd_display.display_image(image)
        else:
            # 通常の会話処理（テキスト応答）
            print("テキスト応答モード: GPT-4o-mini を使用")
            response = chat_with_gpt(text)
            tts_voice.text_to_speech(response)
            print("テキストを表示します")
            epd_display.display_text(response)
        
        subprocess.Popen(['/home/yutapi/myenv/bin/python3', '/home/yutapi/scripts/auto_speaker/ultra_sonic/distance.py'])
                
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        # エラーメッセージを表示
        try:
            epd_display.display_text(f"エラーが発生しました。\n{str(e)}")
        except:
            pass
        
        subprocess.Popen(['python', '/home/yutapi/scripts/auto_speaker/ultra_sonic/distance.py'])
