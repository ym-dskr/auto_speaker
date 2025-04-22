#!/usr/bin/env python3
import os
import sys
import time
import threading
import struct # For converting bytes to int16
import RPi.GPIO as GPIO
import pvporcupine
from pvrecorder import PvRecorder
import simpleaudio as sa

# --- 定数 ---
# プロジェクトのルートディレクトリを取得
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Picovoice モデルディレクトリ (仮) - .ppnファイルへのフルパスを直接指定
# ユーザー指定パス: ~/scripts/auto_speaker/models/picovoice/kikaikun_ja_raspberry-pi_v3_0_0.ppn
# ~ を展開したフルパス
KEYWORD_PATH = "/home/yutapi/scripts/auto_speaker/models/picovoice/kikaikun_ja_raspberry-pi_v3_0_0.ppn"
# 日本語モデルファイルのパス
MODEL_PATH_JA = "/home/yutapi/scripts/auto_speaker/models/picovoice/porcupine_params_ja.pv"
# 音声ファイル保存用ディレクトリ
SOUNDS_DIR = os.path.join(PROJECT_ROOT, "sounds")

# 超音波センサー設定
TRIG_PIN = 15  # GPIO 15
ECHO_PIN = 14  # GPIO 14
SPEED_OF_SOUND = 34370  # 20℃での音速(cm/s)
DISTANCE_THRESHOLD = 20  # 20cm以内で反応

# 検出フラグ（スレッド間で共有）
detection_event = threading.Event()

# --- ログ出力関数 ---
def log_print(*args, **kwargs):
    print(*args, **kwargs, flush=True)

# --- Picovoice Porcupine キーワード検出スレッド ---
def keyword_detection_thread():
    """マイクから音声を取得し、Porcupineでキーワードを検出するスレッド"""
    log_print("キーワード検出スレッド (Porcupine) を開始します...")

    try:
        # Picovoice Access Key を環境変数から取得
        access_key = os.environ.get("PICOVOICE_ACCESS_KEY")
        if not access_key:
            log_print("エラー: 環境変数 PICOVOICE_ACCESS_KEY が設定されていません。")
            return

        # キーワードファイルが存在するか確認
        if not os.path.exists(KEYWORD_PATH):
            log_print(f"エラー: キーワードファイルが見つかりません: {KEYWORD_PATH}")
            return
        log_print(f"使用するキーワードファイル: {KEYWORD_PATH}")

        # 日本語モデルファイルが存在するか確認
        if not os.path.exists(MODEL_PATH_JA):
            log_print(f"エラー: 日本語モデルファイルが見つかりません: {MODEL_PATH_JA}")
            return
        log_print(f"使用する日本語モデルファイル: {MODEL_PATH_JA}")

        # Porcupine ハンドルの初期化 (日本語モデルを指定)
        porcupine = pvporcupine.create(
            access_key=access_key,
            keyword_paths=[KEYWORD_PATH],
            model_path=MODEL_PATH_JA # 日本語モデル指定
            # sensitivity=0.5 # 必要に応じて感度調整 (0.0 ~ 1.0)
        )
        log_print("Porcupine ハンドルを初期化しました。")
        log_print(f"フレーム長: {porcupine.frame_length}, サンプルレート: {porcupine.sample_rate}")

        # PvRecorder の初期化 (Porcupineが必要とするフレーム長とサンプルレートを使用)
        # デフォルトのマイクデバイスを使用
        recorder = PvRecorder(
            frame_length=porcupine.frame_length,
            device_index=-1 # デフォルトデバイス
        )
        recorder.start()
        log_print("音声レコーダーを開始しました。キーワード待機中...")

        while True:
            # オーディオフレームを取得
            pcm = recorder.read()

            # Porcupine でキーワード検出
            result = porcupine.process(pcm)

            if result >= 0:
                log_print(f"キーワード '{os.path.basename(KEYWORD_PATH)}' を検出しました！ (インデックス: {result})")
                play_detection_sound()
                detection_event.set()
                break # 検出したらループを抜ける

    except pvporcupine.PorcupineActivationLimitError:
        log_print("Picovoice 無料枠のアクティベーション制限に達しました。")
    except Exception as e:
        log_print(f"キーワード検出エラー (Porcupine): {e}")
    finally:
        # リソースの解放
        if 'recorder' in locals() and recorder is not None:
            try:
                recorder.stop()
                recorder.delete()
                log_print("音声レコーダーを停止・解放しました。")
            except Exception as e_rec:
                log_print(f"レコーダー解放エラー: {e_rec}")
        if 'porcupine' in locals() and porcupine is not None:
            try:
                porcupine.delete()
                log_print("Porcupine ハンドルを解放しました。")
            except Exception as e_porc:
                log_print(f"Porcupine解放エラー: {e_porc}")

# --- 超音波センサー距離検出スレッド ---
def distance_detection_thread():
    """超音波センサーで距離を測定するスレッド"""
    log_print("距離検出スレッドを開始します...")
    log_print(f"距離しきい値: {DISTANCE_THRESHOLD}cm")

    # GPIOの設定
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(TRIG_PIN, GPIO.OUT)
        GPIO.setup(ECHO_PIN, GPIO.IN)
    except Exception as e:
        log_print(f"GPIO設定エラー: {e}", flush=True)
        log_print("距離検出を無効化します。", flush=True)
        return

    def get_distance():
        """超音波センサーで距離を測定"""
        try:
            # Trigピンを10μsだけHIGHにして超音波の発信開始
            GPIO.output(TRIG_PIN, GPIO.HIGH)
            time.sleep(0.000010)
            GPIO.output(TRIG_PIN, GPIO.LOW)

            # 超音波が発信されるまで待機
            timeout_start = time.time()
            while not GPIO.input(ECHO_PIN):
                if time.time() - timeout_start > 0.1:  # 100ms以上待機したらタイムアウト
                    return float('inf')
                pass
            t1 = time.time()  # 超音波発信時刻（EchoピンがHIGHになった時刻）格納

            # 超音波が受信されるまで待機
            timeout_start = time.time()
            while GPIO.input(ECHO_PIN):
                if time.time() - timeout_start > 0.1:  # 100ms以上待機したらタイムアウト
                    return float('inf')
                pass
            t2 = time.time()  # 超音波受信時刻（EchoピンがLOWになった時刻）格納

            return (t2 - t1) * SPEED_OF_SOUND / 2  # 時間差から対象物までの距離計算
        except Exception as dist_e:
            # log_print(f"距離計算中のエラー: {dist_e}") # デバッグ用
            return float('inf') # エラー時は無限大を返す

    try:
        while True:
            # 検出イベントがセットされたらスレッド終了
            if detection_event.is_set():
                log_print("キーワード検出により距離検出スレッドを終了します。")
                break

            try:
                distance = float('{:.1f}'.format(get_distance()))
                # log_print(f"距離: {distance}cm")  # デバッグ用

                if distance <= DISTANCE_THRESHOLD:
                    log_print(f"距離 {distance}cm <= {DISTANCE_THRESHOLD}cm を検出しました！", flush=True)
                    play_detection_sound()
                    detection_event.set()
                    break # 検出したらループを抜ける
            except Exception as e:
                log_print(f"距離測定ループエラー: {e}", flush=True)

            time.sleep(0.5)  # 0.5秒待機 (少し短縮)

    except KeyboardInterrupt:
        log_print("距離検出スレッドを終了します (KeyboardInterrupt)。")
    except Exception as e:
        log_print(f"距離検出エラー: {e}", flush=True)
    finally:
        # GPIOクリーンアップはメインスレッドで行うためここでは何もしない
        pass

# --- 検出音再生 ---
def play_detection_sound():
    """検出時に音を鳴らす"""
    try:
        beep_path = os.path.join(SOUNDS_DIR, "beep_converted.wav")
        if os.path.exists(beep_path):
            wave_obj = sa.WaveObject.from_wave_file(beep_path)
            play_obj = wave_obj.play()
            # play_obj.wait_done() # wait_done()はブロッキングするので削除
            log_print("検出音を再生しました") # flush=True 削除
        else:
            log_print(f"警告: 検出音ファイルが見つかりません: {beep_path}") # flush=True は元々ない
    except Exception as e:
        log_print(f"音声再生エラー: {e}") # flush=True 削除

# --- メイン処理 ---
def main():
    """メイン処理：検出スレッドを起動し、検出時に正常終了する"""
    log_print("検出システム (Porcupine) を開始します...")

    # スレッドリスト
    threads = []

    try:
        # キーワード検出スレッドを起動
        keyword_thread = threading.Thread(target=keyword_detection_thread)
        keyword_thread.daemon = True
        threads.append(keyword_thread)
        keyword_thread.start()

        # 距離検出スレッドを起動
        distance_thread = threading.Thread(target=distance_detection_thread)
        distance_thread.daemon = True
        threads.append(distance_thread)
        distance_thread.start()

        # 検出イベントを待機 (タイムアウトなし)
        detection_event.wait()

        # 検出されたら正常終了
        log_print("検出されました。正常終了します。", flush=True)

    except KeyboardInterrupt:
        log_print("検出システムを終了します (KeyboardInterrupt)。")
        detection_event.set() # 他のスレッドも終了させる
        sys.exit(1) # エラー終了
    except Exception as e:
        log_print(f"メイン処理でエラーが発生しました: {e}", flush=True)
        detection_event.set() # 他のスレッドも終了させる
        sys.exit(1) # エラー終了
    finally:
        # スレッドの終了を待機 (念のため)
        for t in threads:
            if t.is_alive():
                t.join(timeout=1.0)

        # GPIOをクリーンアップ
        try:
            GPIO.cleanup()
            log_print("GPIO をクリーンアップしました。")
        except Exception as e:
            log_print(f"GPIO cleanup error: {e}", flush=True)

        # 正常終了コードで終了
        sys.exit(0)

if __name__ == "__main__":
    main()
