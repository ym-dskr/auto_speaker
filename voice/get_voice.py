import sounddevice as sd  # マイク入力の録音に使用
import numpy as np  # 数値データ処理のためのライブラリ
import wave  # 音声データをWAVファイルとして保存
import os  # 環境変数取得用
import openai  # OpenAI APIを使用するためのライブラリ
import time  # 処理時間計測用

# APIキーの設定
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("環境変数 'OPENAI_API_KEY' が設定されていません！")

# OpenAI クライアントを作成
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# 録音設定
SAMPLE_RATE = 16000  # 16kHz（Whisper推奨）
THRESHOLD = 1000  # 音のしきい値（環境に応じて調整）
SILENCE_DURATION = 1.0  # 無音が続いたら録音終了（秒）

def is_speaking(audio_chunk):
    """
    音声があるかどうかを判定
    - `THRESHOLD` を超える音が含まれているかチェック
    """
    return np.max(np.abs(audio_chunk)) > THRESHOLD

def record_audio(filename="input.wav"):
    """
    しゃべり始めと終わりを検知して録音する。
    """
    print("録音を待機中...")
    
    recording = []
    silence_counter = 0
    is_recording = False

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype=np.int16) as stream:
        while True:
            audio_chunk, _ = stream.read(int(SAMPLE_RATE * 0.1))  # 100msごとに音声を取得
            recording.append(audio_chunk)

            if is_speaking(audio_chunk):  # 発話を検知
                if not is_recording:
                    print("録音開始！")
                    is_recording = True
                silence_counter = 0  # 無音カウンターをリセット
            elif is_recording:  # すでに録音中なら無音をカウント
                silence_counter += 0.1
                if silence_counter > SILENCE_DURATION:
                    print("録音終了。")
                    break  # 無音が続いたら録音終了

    # 録音データをWAVファイルに保存
    audio_data = np.concatenate(recording, axis=0)
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio_data.tobytes())

    return filename  # 録音したファイルのパスを返す

def transcribe_audio(filename="input.wav"):
    """
    OpenAI Whisper APIを使って音声をテキストに変換する。
    日本語に最適化しており、より高速に動作する。
    """
    print("文字起こしを開始...")
    start_time = time.time()  # 処理時間計測開始
    
    try:
        with open(filename, "rb") as audio_file:
            # OpenAI Whisper APIを呼び出し
            response = client.audio.transcriptions.create(
                model="whisper-1",  # 最新のWhisperモデル
                file=audio_file,
                language="ja",  # 日本語を指定
                response_format="text"  # テキスト形式で返す
            )
        
        elapsed_time = time.time() - start_time
        print(f"文字起こし完了（処理時間: {elapsed_time:.2f}秒）")
        return response  # API応答のテキストを返す
    
    except Exception as e:
        print(f"文字起こしエラー: {e}")
        return "音声認識に失敗しました。もう一度お試しください。"


if __name__ == "__main__":
    # 録音を実行し、ファイルを取得
    audio_file = record_audio()

    # 音声認識を実行し、テキストを取得
    text = transcribe_audio(audio_file)

    # 認識結果を表示
    print("認識結果:", text)
