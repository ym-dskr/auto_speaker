import os
import openai
import requests
from io import BytesIO
from PIL import Image
from display import epd_display
import datetime
import re

# OpenAI APIキーを環境変数から取得
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("環境変数 'OPENAI_API_KEY' が設定されていません！")

# OpenAI クライアントを作成
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# 事前設定（システムメッセージ）
SYSTEM_PROMPT = """
    # 知らない単語の組み合わせや熟語が出た場合は、話者に聞き返してください。
    # あなたは大阪弁の博識で元気なアドバイザーです。
    # 全ての分野に精通しています。
    # ユーザの子供であるたけまさくん（男）、めいちゃん（女）の2人の子供に話しかけることがあります。
    # ユーザの子供であるさわちゃん（女）もいますが、0歳でまだ小さいです。
    # 簡潔かつわかりやすく、具体的な回答をしてください。
    # !?以外の記号・絵文字は使用しません。
    """
# """
#     # あなたは大阪在住のおばちゃんです。
#     # 簡潔かつわかりやすく、具体的な回答をしてください。
#     # ジョークを交えた大阪弁で面白おかしく、スーパーハイテンションで回答します。
#     # 絵文字は使用しません。
#     """

def generate_image(prompt):
    """
    DALL·E を使用して画像を生成
    """
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        n=1,
        size="1792x1024"
    )

    image_url = response.data[0].url
    return image_url


def download_and_resize_image(image_url, target_size=(800, 480)):
    """
    画像をダウンロードし、800x480にリサイズ
    """
    response = requests.get(image_url)
    image = Image.open(BytesIO(response.content))

    # 画像を正確に800x480にリサイズ（アスペクト比は保持しない）
    try:
        # Pillow 9.0.0以降
        from PIL.Image import Resampling

        image = image.resize(target_size, Resampling.LANCZOS)
    except (ImportError, AttributeError):
        # 古いバージョンのPillow
        image = image.resize(target_size, Image.LANCZOS)

    # サイズを確認（デバッグ用）
    print(f"リサイズ後の画像サイズ: {image.size}")

    return image


def sanitize_filename(text, max_length=50):
    """
    ファイル名に使用できない文字を削除し、最大長さを制限
    """
    # 変数を初期化
    sanitized = text

    # ファイル名に使えない文字を削除
    sanitized = re.sub(r"[\\/*?:\"><|]", "", sanitized)

    # スペースをアンダースコアに置換
    sanitized = sanitized.replace(" ", "_")

    # 先頭と末尾の空白と句読点を削除
    sanitized = sanitized.strip(" 　.,。、")

    # 長すぎる場合は切り詰め
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    # 空文字になった場合のデフォルト名
    if not sanitized:
        sanitized = "image"

    return sanitized


def save_image(image, prompt):
    """
    画像を入力文字列と日付を含むファイル名で保存
    """
    # 画像保存用のディレクトリを作成（存在しない場合）
    images_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "generated_images"
    )
    os.makedirs(images_dir, exist_ok=True)

    # ファイル名を作成: 日付_入力テキスト.png
    now = datetime.datetime.now()
    date_str = now.strftime("%Y%m%d_%H%M%S")
    sanitized_prompt = sanitize_filename(prompt)
    filename = f"{date_str}_{sanitized_prompt}.png"

    # ファイルパスを作成
    filepath = os.path.join(images_dir, filename)

    # 画像を保存
    image.save(filepath)
    print(f"画像を保存しました: {filepath}")

    return filepath


def chat_with_gpt(prompt, history):
    """
    OpenAI API にテキストを送信し、GPT-4oの応答を取得し、その応答が質問かどうかを判定する
    会話履歴を考慮する
    """
    # 1. 会話履歴にユーザーのプロンプトを追加
    current_history = history + [{"role": "user", "content": prompt}]

    # 2. ユーザーのプロンプトに対する応答を取得 (会話履歴全体を渡す)
    response_obj = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=current_history
    )
    gpt_response_content = response_obj.choices[0].message.content

    # 3. 会話履歴にGPTの応答を追加
    updated_history = current_history + [{"role": "assistant", "content": gpt_response_content}]

    # 4. 取得した応答が質問かどうかをGPTに判断させる
    messages_for_check = [
        {"role": "system", "content": "あなたはテキストがユーザーに追加の応答を求める質問であるかどうかを判断するAIです。「はい」か「いいえ」のみで答えてください。"},
        {"role": "user", "content": f"以下のテキストはユーザーに追加の応答を求める質問ですか？\n\n{gpt_response_content}"}
    ]
    check_response_obj = client.chat.completions.create(
        model="gpt-4o-mini", # より高速なモデルでも良いかもしれない
        messages=messages_for_check,
        max_tokens=5 # 「はい」か「いいえ」だけを期待
    )
    check_result = check_response_obj.choices[0].message.content.strip()

    # 質問かどうかを判定
    is_question = "はい" in check_result

    return gpt_response_content, is_question, updated_history

def summarize_text_for_display(text, max_chars=700):
    """
    与えられたテキストを電子ペーパー表示用に指定文字数以内で要約する
    """
    summarize_prompt = f"""以下のテキストを、最も重要な要点のみを残して{max_chars}文字以内で簡潔に大阪弁で要約してください。
    

                        テキスト：{text}

                        要約：
                        """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", # 要約タスクにはこれで十分な場合が多い
            messages=[
                {"role": "system", "content": "あなたはテキストを要約するAIです。指定された文字数制限を厳守してください。"},
                {"role": "user", "content": summarize_prompt}
            ],
            max_tokens=int(max_chars * 1.5) # 文字数制限より少し多めにトークンを確保
        )
        summary = response.choices[0].message.content.strip()
        
        # 念のため文字数チェックと切り詰め
        if len(summary) > max_chars:
            summary = summary[:max_chars]
            
        return summary
    except Exception as e:
        print(f"要約中にエラーが発生しました: {e}")
        # エラー時は元のテキストを切り詰めて返すなどのフォールバックも検討可能
        return text[:max_chars]


if __name__ == "__main__":
    None
