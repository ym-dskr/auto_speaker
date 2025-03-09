import get_voice  # 録音 & Whisper
import chat  # GPT-4 API

if __name__ == "__main__":
    # 音声録音 & Whisper でテキスト化
    audio_file = get_voice.record_audio()
    text = get_voice.transcribe_audio(audio_file)
    print("認識結果:", text)

    # GPT-4 に問い合わせ
    response = chat.chat_with_gpt(text)
    print("GPT-4の応答:", response)
