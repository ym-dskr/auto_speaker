from voice import get_voice
from api import chat
from api import tts_voice
from display import epd_display
from camera import camera_control
from PIL import Image
import requests
from io import BytesIO
import re

def check_for_camera_command(text):
    """
    テキスト内に「はいチーズ」や「はい、チーズ」のような写真撮影コマンドが含まれているか確認
    """
    # より柔軟な正規表現パターン（「チーズ」のカタカナ表記や濁音も許容）
    patterns = [
        r'はい.*チーズ',      # 「はい」の後に何か文字があって「チーズ」
        r'はい.*ちーず',      # ひらがな表記
        r'はい.*ティーズ',    # カタカナ混じり表記
        r'はい.*cheese',     # ローマ字表記も許容
        r'チーズ',            # 単に「チーズ」だけでも許容
        r'ちーず'             # ひらがな表記
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
    
    # 単純な部分文字列チェック（正規表現でマッチしない場合のバックアップ）
    # simple_checks = ["はい", "チーズ", "ちーず"]
    # for check in simple_checks:
    #     if check in text_lower:
    #         print(f"単純一致: {check}")
    #         # 「はい」と「チーズ/ちーず」の両方が含まれているかチェック
    #         if ("はい" in text_lower) and (("チーズ" in text_lower) or ("ちーず" in text_lower)):
    #             print("「はい」と「チーズ/ちーず」の両方を検出")
    #             return True
    
    print("写真撮影コマンドは検出されませんでした")
    return False

if __name__ == "__main__":
    try:
        # 音声録音 & Whisper でテキスト化
        audio_file = get_voice.record_audio()
        text = get_voice.transcribe_audio(audio_file)
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
            
        else:
            # 通常の会話処理（画像生成またはテキスト応答）
            response = chat.handle_request(text)

            if response["type"] == "image":
                print("画像を表示します")
                # 画像オブジェクトを直接使用（URLからの再ダウンロードは不要）
                image = response["image"]
                epd_display.display_image(image)
            else:
                # 音声発話
                tts_voice.text_to_speech(response["content"])
                print("テキストを表示します")
                # 回答表示
                epd_display.display_text(response["content"])
                
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        # エラーメッセージを表示
        try:
            epd_display.display_text(f"エラーが発生しました。\n{str(e)}")
        except:
            pass
