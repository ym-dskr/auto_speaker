import openai
from openai import OpenAI
import os
import requests
import simpleaudio as sa
from pydub import AudioSegment  # MP3 → WAV 変換用

# OpenAI APIキーを環境変数から取得
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# プロジェクトのルートディレクトリを取得
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 音声ファイル保存用ディレクトリ
SOUNDS_DIR = os.path.join(PROJECT_ROOT, "sounds")
# ディレクトリが存在しない場合は作成
os.makedirs(SOUNDS_DIR, exist_ok=True)

def text_to_speech(text, mp3_filename=None, wav_filename=None):
    """
    OpenAIのTTS APIを使って、日本語音声を生成し、MP3をWAVに変換して再生する。
    mp3_filename, wav_filenameが指定されていない場合は、soundsディレクトリにresponse.mp3, response.wavとして保存する。
    """
    # デフォルトのファイル名を設定（sounds/ディレクトリに格納）
    if mp3_filename is None:
        mp3_filename = os.path.join(SOUNDS_DIR, "response.mp3")
    elif not os.path.isabs(mp3_filename):  # 相対パスが指定された場合
        mp3_filename = os.path.join(SOUNDS_DIR, mp3_filename)
        
    if wav_filename is None:
        wav_filename = os.path.join(SOUNDS_DIR, "response.wav")
    elif not os.path.isabs(wav_filename):  # 相対パスが指定された場合
        wav_filename = os.path.join(SOUNDS_DIR, wav_filename)
    
    client = OpenAI()
    
    response = client.audio.speech.create(
        model="gpt-4o-mini-tts", # 最新のTTSモデル
        input=text,
        voice="nova",
        instructions="Speak in a cheerful and positive tone like Japanese.",
        response_format="mp3",
    )
    
    # MP3 ファイルに保存
    with open(mp3_filename, "wb") as f:
        f.write(response.content)
    print(f"音声ファイルを保存しました: {mp3_filename}")

    # MP3 → WAV に変換
    sound = AudioSegment.from_file(mp3_filename, format="mp3")
    sound.export(wav_filename, format="wav")
    print(f"WAVファイルに変換しました: {wav_filename}")

    # WAV を再生
    wave_obj = sa.WaveObject.from_wave_file(wav_filename)
    wave_obj.play().wait_done()

if __name__ == "__main__":
    text = "こんにちは、元気ですか？"
    text_to_speech(text)
