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

# プロジェクトのルートディレクトリを取得
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 音声ファイル保存用ディレクトリ
SOUNDS_DIR = os.path.join(PROJECT_ROOT, "sounds")
# ディレクトリが存在しない場合は作成
os.makedirs(SOUNDS_DIR, exist_ok=True)

# 録音ファイルのパスを固定
INPUT_WAV_PATH = os.path.join(SOUNDS_DIR, "input.wav")

# 録音設定
SAMPLE_RATE = 16000  # 16kHz（Whisper推奨）
THRESHOLD = 1000  # 音のしきい値（環境に応じて調整） - 無音判定用
THRESHOLD_START_RECORDING = 5000  # 録音開始の音量しきい値 - より大きく設定して偶発的な録音を防止
SILENCE_DURATION = 2.0  # 無音が続いたら録音終了（秒）

def is_speaking(audio_chunk, threshold=THRESHOLD):
    """
    音声があるかどうかを判定
    - `threshold` を超える音が含まれているかチェック
    - しきい値を引数で指定可能（録音開始/終了で異なる値を使用）
    """
    return np.max(np.abs(audio_chunk)) > threshold

def record_audio():
    """
    音声検知から開始し、話し終わって1秒後に終了する録音機能
    - 録音開始には高いしきい値を使用
    - 録音中の無音検知には低いしきい値を使用
    - 固定パス(sounds/input.wav)に保存
    """
    print("音声入力を待機中... 話しかけてください")
    
    # タイムアウト設定
    start_time = time.time()
    timeout = 10  # 秒

    # 録音前のバッファ（録音には含めない）
    pre_recording = []
    # 実際の録音データ
    recording = []
    silence_counter = 0
    is_recording = False
    waiting_for_speech = True

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype=np.int16) as stream:
        while True:
            audio_chunk, _ = stream.read(int(SAMPLE_RATE * 0.1))  # 100msごとに音声を取得
            
            # タイムアウトチェック
            if waiting_for_speech and (time.time() - start_time) > timeout:
                print(f"{timeout}秒経過 - タイムアウト")
                return None  # タイムアウト時はNoneを返す
            
            if waiting_for_speech:
                # 音声検知前の状態（まだ録音開始していない）
                if is_speaking(audio_chunk, THRESHOLD_START_RECORDING):  # 高いしきい値で録音開始判定
                    print("音声を検知しました - 録音開始")
                    waiting_for_speech = False
                    is_recording = True
                    # 直前の少しのデータも含める（発話の最初の部分を逃さないため）
                    if len(pre_recording) > 5:  # 最大0.5秒分の直前の音声を含める
                        recording.extend(pre_recording[-5:])
                    recording.append(audio_chunk)
                else:
                    # 発話前の音声を一時バッファに保存（古いものを削除）
                    pre_recording.append(audio_chunk)
                    if len(pre_recording) > 10:  # 最大1秒分を保持
                        pre_recording.pop(0)
            elif is_recording:
                # 録音中の状態
                recording.append(audio_chunk)
                
                if is_speaking(audio_chunk):  # 通常のしきい値で無音判定
                    # 音声を検知
                    silence_counter = 0  # 無音カウンターをリセット
                else:
                    # 無音を検知
                    silence_counter += 0.1
                    if silence_counter >= SILENCE_DURATION:
                        print(f"無音を{SILENCE_DURATION}秒検知 - 録音終了")
                        break  # 無音が続いたら録音終了

    if not recording:
        print("音声が検出されませんでした。もう一度試してください。")
        return record_audio()  # 再帰的に再試行
    
    # 録音データをWAVファイルに保存
    print("録音データを保存中...")
    audio_data = np.concatenate(recording, axis=0)
    with wave.open(INPUT_WAV_PATH, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio_data.tobytes())

    print(f"録音完了 - 長さ: {len(audio_data)/SAMPLE_RATE:.2f}秒 - 保存先: {INPUT_WAV_PATH}")
    return INPUT_WAV_PATH  # 録音したファイルのパスを返す

def transcribe_audio():
    """
    OpenAI Whisper APIを使って音声をテキストに変換する。
    日本語に最適化しており、より高速に動作する。
    固定パス(sounds/input.wav)から読み込み
    """
    print("文字起こしを開始...")
    start_time = time.time()  # 処理時間計測開始
    
    try:
        with open(INPUT_WAV_PATH, "rb") as audio_file:
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
    record_audio()

    # 音声認識を実行し、テキストを取得
    text = transcribe_audio()

    # 認識結果を表示
    print("認識結果:", text)
