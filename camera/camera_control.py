import os
import datetime
from picamera2 import Picamera2
import time
from PIL import Image
import numpy as np
import sys
sys.path.append('/home/yutapi/scripts')  # プロジェクトのルートディレクトリをパスに追加
# 音声読み上げは削除、ビープ音機能だけを残す
import simpleaudio as sa
import wave

# 写真保存ディレクトリ
PHOTOS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "photos")
os.makedirs(PHOTOS_DIR, exist_ok=True)

# 音声フィードバック用のサウンドファイルディレクトリ
SOUNDS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sounds")
os.makedirs(SOUNDS_DIR, exist_ok=True)

def play_beep():
    """
    ビープ音を鳴らす（カウントダウン用）
    """
    # ビープ音のパラメータ
    frequency = 1000  # Hz
    duration = 0.2    # 秒
    sample_rate = 44100  # サンプルレート
    
    # サイン波を生成
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    tone = np.sin(frequency * t * 2 * np.pi)
    
    # 音量調整（最大値を32767に）
    audio = tone * 32767 / np.max(np.abs(tone))
    audio = audio.astype(np.int16)
    
    # 再生
    play_obj = sa.play_buffer(audio, 1, 2, sample_rate)
    play_obj.wait_done()

def play_shutter_sound():
    """
    シャッター音を鳴らす
    """
    # シャッター音のファイルパス
    shutter_sound_path = os.path.join(SOUNDS_DIR, "shutter.wav")
    
    # ファイルがない場合は作成
    if not os.path.exists(shutter_sound_path):
        # シャッター音を生成（クリック音）
        sample_rate = 44100
        duration = 0.3
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        
        # クリック音の生成（急激な立ち上がりと減衰）
        click = np.exp(-t * 30) * np.sin(2000 * t * 2 * np.pi)
        audio = click * 32767 / np.max(np.abs(click))
        audio = audio.astype(np.int16)
        
        # WAVファイルとして保存
        with wave.open(shutter_sound_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio.tobytes())
    
    # 音声ファイルを再生
    wave_obj = sa.WaveObject.from_wave_file(shutter_sound_path)
    play_obj = wave_obj.play()
    play_obj.wait_done()

def capture_photo(filename=None):
    """
    Raspberry Piカメラで写真を撮影し、指定されたファイル名で保存
    カウントダウンと撮影時にビープ音によるフィードバックを提供
    戻り値: 保存したファイルのパスとPIL Imageオブジェクト
    """
    print("カメラを準備中...")
    
    # カメラの初期化
    picam2 = Picamera2()
    
    # カメラの設定
    config = picam2.create_still_configuration(
        main={"size": (1920, 1080)},  # 解像度は必要に応じて調整可能
        lores={"size": (800, 480)},  # 電子ペーパーの解像度に合わせたプレビュー
        display="lores"
    )
    picam2.configure(config)
    
    # カメラの起動
    picam2.start()
    
    # カメラの安定化のための待機
    time.sleep(2)  # カメラが起動して安定するまで待機
    
    print("3秒後に撮影します...")
    # カウントダウン
    for i in range(3, 0, -1):
        print(f"{i}...")
        # ビープ音を鳴らす
        play_beep()
        time.sleep(0.8)  # カウント間の間隔を少し長めに
    
    # 撮影を知らせる短いビープ音を2回鳴らす
    play_beep()
    time.sleep(0.1)
    play_beep()
    
    # シャッター音を鳴らす
    play_shutter_sound()
    print("チーズ！")
    
    # 写真の撮影
    array = picam2.capture_array()
    
    # カメラを停止
    picam2.stop()
    
    # numpy arrayからPIL Imageへ変換
    img = Image.fromarray(array)
    
    # ファイル名が指定されていない場合は現在日時を使用
    if filename is None:
        now = datetime.datetime.now()
        date_str = now.strftime("%Y%m%d_%H%M%S")
        filename = f"photo_{date_str}.jpg"
    
    # 写真の保存パス
    filepath = os.path.join(PHOTOS_DIR, filename)
    
    # 写真を保存
    img.save(filepath)
    print(f"写真を保存しました: {filepath}")
    
    return filepath, img

def resize_for_epaper(img, target_size=(800, 480)):
    """
    撮影した写真を電子ペーパーディスプレイ用にリサイズ
    """
    # 画像をリサイズ
    try:
        from PIL.Image import Resampling
        img_resized = img.resize(target_size, Resampling.LANCZOS)
    except (ImportError, AttributeError):
        img_resized = img.resize(target_size, Image.LANCZOS)
    
    return img_resized

# テスト用のメイン処理
if __name__ == "__main__":
    # 写真を撮影
    filepath, img = capture_photo()
    
    # 撮影した写真のサイズを表示
    print(f"撮影画像サイズ: {img.size}")
    
    # 電子ペーパー用にリサイズ
    img_epaper = resize_for_epaper(img)
    print(f"リサイズ後サイズ: {img_epaper.size}") 