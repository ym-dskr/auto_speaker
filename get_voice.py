import sounddevice as sd  # マイク入力の録音に使用
import numpy as np  # 数値データ処理のためのライブラリ
import wave  # 音声データをWAVファイルとして保存
import subprocess  # Whisperの実行を行うためのライブラリ（外部コマンド実行）

# サンプリングレート（音声データの品質設定）
SAMPLE_RATE = 16000  # 16kHz（Whisperの推奨値）
DURATION = 5  # 録音時間（秒）

def record_audio(filename="input.wav"):
    """
    マイクから音声を録音し、WAVファイルとして保存する。
    """
    print("録音開始...")
    # 録音開始（モノラル1チャンネル、16bit整数型）
    audio = sd.rec(int(SAMPLE_RATE * DURATION), samplerate=SAMPLE_RATE, channels=1, dtype=np.int16)
    sd.wait()  # 録音終了を待機
    print("録音終了。")

    # WAVファイルに保存
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(1)  # モノラル音声
        wf.setsampwidth(2)  # 16bit（2バイト）
        wf.setframerate(SAMPLE_RATE)  # 16kHz
        wf.writeframes(audio.tobytes())  # 録音データを書き込み

    return filename  # 録音したファイルのパスを返す

def transcribe_audio(filename="input.wav"):
    """
    Whisperを使って音声を日本語でテキストに変換する。
    """
    result = subprocess.run([
        "/home/yutapi/whisper.cpp/build/bin/whisper-cli",  # Whisper CLI 実行ファイル
        "-m", "/home/yutapi/whisper.cpp/models/ggml-base.bin",  # 日本語対応モデル
        "-l", "ja",  # 言語を日本語に固定
        "-f", filename  # 解析する音声ファイル
    ], capture_output=True, text=True)

    return result.stdout.strip()  # Whisperの出力結果を返す


if __name__ == "__main__":
    # 録音を実行し、ファイルを取得
    audio_file = record_audio()

    # 音声認識を実行し、テキストを取得
    text = transcribe_audio(audio_file)

    # 認識結果を表示
    print("認識結果:", text)
