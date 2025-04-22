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
import tempfile # 一時ファイル用に追加
from display import epdconfig  # EPDリソース解放のためにインポート
from api import tts_voice, chat_with_gpt
from api.chat import (
    SYSTEM_PROMPT,
    summarize_text_for_display,
    generate_greeting,
    generate_farewell,
)  # generate_farewell をインポート


load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")


def is_image_request(prompt):
    """
    ユーザーの入力が画像生成の指示かどうかを判定
    """
    keywords = [
        "絵を描いて",
        "イラストを作って",
        "画像を生成",
        "写真を作成",
        "描いて",
    ]
    return any(keyword in prompt for keyword in keywords)


def check_for_camera_command(text):
    """
    テキスト内に「はいチーズ」や「はい、チーズ」のような写真撮影コマンドが含まれているか確認
    """
    # より柔軟な正規表現パターン（「チーズ」のカタカナ表記や濁音も許容）
    patterns = [
        r"はい.*チーズ",  # 「はい」の後に何か文字があって「チーズ」
        r"はい.*ちーず",  # ひらがな表記
        r"はい.*ティーズ",  # カタカナ混じり表記
        r"はい.*キーズ",
        r"はい.*cheese",  # ひらがな表記
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


# 一時ファイルのパスを定義 (web_trigger.py と合わせる)
TRIGGER_FILE_PATH = os.path.join(tempfile.gettempdir(), "conversation_starter.txt")

if __name__ == "__main__":

    initial_prompt_from_web = None
    start_sound_path = "/home/yutapi/scripts/auto_speaker/sounds/start.wav"
    beep_sound_path = "/home/yutapi/scripts/auto_speaker/sounds/beep_converted.wav"
            
    # --- 起動時にWebトリガーファイルを確認 ---
    if os.path.exists(TRIGGER_FILE_PATH):
        try:
            with open(TRIGGER_FILE_PATH, 'r', encoding='utf-8') as f:
                initial_prompt_from_web = f.read().strip()
            os.remove(TRIGGER_FILE_PATH) # 読み込んだら削除
            print(f"Webからの初期プロンプトを読み込みました: '{initial_prompt_from_web[:50]}...'")
        except Exception as e:
            print(f"トリガーファイルの読み込み/削除に失敗: {e}")
            initial_prompt_from_web = None # 失敗したらNoneに戻す
    # --- ここまで追加 ---

    # wave_obj = sa.WaveObject.from_wave_file(
    #         "/home/yutapi/scripts/auto_speaker/sounds/beep_converted.wav"
    #         )
    # wave_obj.play().wait_done()
    # --- メイン処理全体を try...finally で囲む ---
    try:
        # --- 起動時の挨拶処理を変更 ---
        # Webトリガーでない場合のみ起動音を再生
        if initial_prompt_from_web is None:
            print("通常の起動です。起動音を再生します。")
            # 起動音を再生 (start.wav があればそれを優先、なければ beep_converted.wav)
            try:
                if os.path.exists(start_sound_path):
                    wave_obj = sa.WaveObject.from_wave_file(start_sound_path)
                    print("起動音 (start.wav) を再生します。")
                else:
                    wave_obj = sa.WaveObject.from_wave_file(beep_sound_path)
                    print("起動音 (beep_converted.wav) を再生します。")
                wave_obj.play().wait_done()

                wave_obj = sa.WaveObject.from_wave_file(
                            "/home/yutapi/scripts/auto_speaker/sounds/continue.wav"
                       )
                wave_obj.play().wait_done()
            except Exception as e:
                print(f"起動音の再生中にエラーが発生しました: {e}")
        else:
            print("Webトリガーによる起動です。起動音はスキップします。")
        # --- ここまで変更 ---

        # 会話履歴を初期化 (システムプロンプトを含む)
        conversation_history = [{"role": "system", "content": SYSTEM_PROMPT}]
        text = None # 認識結果テキストを初期化

        try:
            # --- Webからの入力があれば音声認識をスキップ ---
            if initial_prompt_from_web:
                text = initial_prompt_from_web
                print("Webからの入力を使用します。音声認識はスキップします。")
                # このブロック内の会話処理は削除。後続の共通処理ブロックで行う。
            else:
                # 従来通り音声認識を実行
                print("音声認識を開始します。")
                audio_file = get_voice.record_audio()
                if audio_file is None:
                    print("音声入力がタイムアウトしました。")
                    farewell_text = generate_farewell()  # 別れの挨拶を生成
                    print(f"生成された別れの挨拶: {farewell_text}")
                    tts_voice.text_to_speech(farewell_text)  # 音声合成して再生
                    # distance.py の呼び出しは systemd に任せるため削除
                    sys.exit()  # main.py を終了させることで systemd が distance.py を再実行する
                text = get_voice.transcribe_audio()
            # ここまで変更 ---
            # 雑音やほぼ無音と判断された場合（Noneが返された場合）
                if text is None:
                    print("雑音やほぼ無音と判断されました。会話を終了します。")
                    farewell_text = generate_farewell()  # 別れの挨拶を生成
                    print(f"生成された別れの挨拶: {farewell_text}")
                    tts_voice.text_to_speech(farewell_text)  # 音声合成して再生
                    # distance.py の呼び出しは systemd に任せるため削除
                    sys.exit()  # main.py を終了させることで systemd が distance.py を再実行する
            # text = get_voice.transcribe_audio() # Commented out by user
            # if text is None: # Commented out by user
            #     # ... handle None text ... # Commented out by user

            # --- ここから共通処理 ---
            if text is None:
                 # このケースは音声認識失敗時のみのはずだが念のため
                 print("有効なテキスト入力がありません。処理を終了します。")
                 # 必要なら別れの挨拶
                 farewell_text = generate_farewell()
                 tts_voice.text_to_speech(farewell_text)
                 sys.exit()

            print("認識結果:", text)

            # --- 特殊コマンド処理 ---
            processed_special_command = False # 特殊コマンドを処理したかどうかのフラグ
            if check_for_camera_command(text):
                print("写真撮影コマンドを検出しました！")
                # 写真を撮影
                photo_path, photo_image = camera_control.capture_photo()
                print(f"写真を保存しました: {photo_path}")
                # 撮影した写真を電子ペーパーに表示
                epd_display.display_image(photo_image)
                print("写真を電子ペーパーに表示しました")
                processed_special_command = True # カメラコマンドを処理した
            elif is_image_request(text):
                # 画像生成
                print("画像生成モード: DALL·E を使用")
                image_url = generate_image(text)
                image = download_and_resize_image(image_url)
                save_image(image, text)
                epd_display.display_image(image)
                processed_special_command = True # 画像生成コマンドを処理した

            # --- 通常の会話処理 (特殊コマンドが処理されなかった場合) ---
            if not processed_special_command:
                print("テキスト応答モード: GPT-4o-mini を使用")
                response, is_question, conversation_history = chat_with_gpt(
                    text, conversation_history
                )  # 履歴を渡し、更新された履歴を受け取る
                tts_voice.text_to_speech(response)
                if not is_question:
                    print("応答を要約して表示します...")
                    summary = summarize_text_for_display(response)  # 応答を要約
                    print("要約:", summary)
                    epd_display.display_text(summary)  # 要約を表示
                # GPTの応答が質問の場合、会話を継続
                while is_question:
                    print("GPTが質問をしました。会話を継続します。")
                    # 会話継続を知らせる音声を再生
                    wave_obj = sa.WaveObject.from_wave_file(
                        "/home/yutapi/scripts/auto_speaker/sounds/continue.wav"
                    )
                    wave_obj.play().wait_done()
                    # 音声録音 & Whisper でテキスト化
                    audio_file = get_voice.record_audio()
                    if audio_file is None:
                        print("音声入力がタイムアウトしました。最後の応答を要約して表示します。")
                        farewell_text = generate_farewell()  # 別れの挨拶を生成
                        print(f"生成された別れの挨拶: {farewell_text}")
                        tts_voice.text_to_speech(farewell_text)  # 音声合成して再生
                        # タイムアウト前の最後の応答 (response) を要約して表示
                        summary = summarize_text_for_display(response)
                        print("要約:", summary)
                        epd_display.display_text(summary)
                        break
                    text = get_voice.transcribe_audio()
                    print("認識結果:", text)
                    response, is_question, conversation_history = chat_with_gpt(
                        text, conversation_history
                    )  # 履歴を渡し、更新された履歴を受け取る
                    tts_voice.text_to_speech(response)
                    if not is_question:
                        print("応答を要約して表示します...")
                        summary = summarize_text_for_display(response)  # 応答を要約
                        print("要約:", summary)
                        epd_display.display_text(summary)  # 要約を表示
        except Exception as e:
            print(f"エラーが発生しました: {str(e)}")
            # エラーメッセージを表示
            try:
                epd_display.display_text(f"エラーが発生しました。\n{str(e)}")
            except:
                pass
    # --- finally ブロックで EPD リソースを解放 ---
    finally:
        print("Cleaning up EPD resources...")
        try:
            epdconfig.module_exit()  # GPIOピンとSPIを解放
            print("EPD resources cleaned up.")
        except Exception as cleanup_e:
            print(f"Error during EPD cleanup: {cleanup_e}")
        sys.exit() 
