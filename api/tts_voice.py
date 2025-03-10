import openai
import os
import requests
import simpleaudio as sa
from pydub import AudioSegment  # MP3 → WAV 変換用

# OpenAI APIキーを環境変数から取得
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def text_to_speech(text, mp3_filename="response.mp3", wav_filename="response.wav"):
    """
    OpenAIのTTS APIを使って、日本語音声を生成し、MP3をWAVに変換して再生する。
    """
    url = "https://api.openai.com/v1/audio/speech"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "tts-1",  # 最新のTTSモデル
        "input": text,
        "voice": "nova"  # 話者の選択（alloy, echo, fable, onyx, nova, shimmer）
    }
    response = requests.post(url, headers=headers, json=data)

    # MP3 ファイルに保存
    with open(mp3_filename, "wb") as f:
        f.write(response.content)

    # MP3 → WAV に変換
    sound = AudioSegment.from_file(mp3_filename, format="mp3")
    sound.export(wav_filename, format="wav")

    # WAV を再生
    wave_obj = sa.WaveObject.from_wave_file(wav_filename)
    wave_obj.play().wait_done()

if __name__ == "__main__":
    text = "こんにちは、元気ですか？"
    text_to_speech(text)
