from voice import get_voice
from api import chat
from api import tts_voice
from display import epd_display
from PIL import Image
import requests
from io import BytesIO

if __name__ == "__main__":
    # 音声録音 & Whisper でテキスト化
    audio_file = get_voice.record_audio()
    text = get_voice.transcribe_audio(audio_file)
    print("認識結果:", text)

    # 入力に応じて、画像生成かテキスト応答を選択し処理する
    response = chat.handle_request(text)

    if response["type"] == "image":
        print("画像を表示します")
        # 画像オブジェクトを直接使用（URLからの再ダウンロードは不要）
        image = response["image"]
        chat.display_image_on_epaper(image)
    else:
        print("テキストを表示します")
        # 回答表示
        epd_display.display_text(response["content"])
        # 音声発話
        tts_voice.text_to_speech(response["content"])
