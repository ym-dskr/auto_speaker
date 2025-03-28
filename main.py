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
import simpleaudio as sa  # simpleaudio は不要になる可能性あり
from display import epdconfig  # EPDリソース解放のためにインポート

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


if __name__ == "__main__":
    # --- メイン処理全体を try...finally で囲む ---
    try:
        from api import tts_voice, chat_with_gpt
        from api.chat import (
            SYSTEM_PROMPT,
            summarize_text_for_display,
            generate_greeting,
            generate_farewell,
        )  # generate_farewell をインポート
        # GPTによる挨拶を生成して再生
        try:
            greeting_text = generate_greeting()
            print(f"生成された挨拶: {greeting_text}")
            tts_voice.text_to_speech(greeting_text)
            # 会話継続を知らせる音声を再生
            wave_obj = sa.WaveObject.from_wave_file(
                "/home/yutapi/scripts/auto_speaker/sounds/continue.wav"
            )
            wave_obj.play().wait_done()
        except Exception as e:
            print(f"挨拶の生成または再生中にエラーが発生しました: {e}")
            # エラー時もデフォルトの音声を再生するなど、フォールバック処理を追加しても良い
            try:
                # デフォルトの音声ファイルがあれば再生
                wave_obj = sa.WaveObject.from_wave_file(
                    "/home/yutapi/scripts/auto_speaker/sounds/start.wav"
                )
                wave_obj.play().wait_done()
            except Exception as audio_e:
                print(f"デフォルト音声の再生に失敗しました: {audio_e}")
        # 会話履歴を初期化 (システムプロンプトを含む)
        conversation_history = [{"role": "system", "content": SYSTEM_PROMPT}]
        try:
            # 音声録音 & Whisper でテキスト化
            audio_file = get_voice.record_audio()
            if audio_file is None:
                print("音声入力がタイムアウトしました。")
                farewell_text = generate_farewell()  # 別れの挨拶を生成
                print(f"生成された別れの挨拶: {farewell_text}")
                tts_voice.text_to_speech(farewell_text)  # 音声合成して再生
                # distance.py の呼び出しは systemd に任せるため削除
                sys.exit()  # main.py を終了させることで systemd が distance.py を再実行する
            text = get_voice.transcribe_audio()
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
            elif is_image_request(text):
                # 画像生成
                print("画像生成モード: DALL·E を使用")
                image_url = generate_image(text)
                image = download_and_resize_image(image_url)
                save_image(image, text)
                epd_display.display_image(image)
            else:
                # 通常の会話処理（テキスト応答）
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
