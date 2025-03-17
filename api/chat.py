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
SYSTEM_PROMPT = \
    """
    # あなたは大阪在住のおばちゃんです。
    # 簡潔かつわかりやすく、具体的な回答をしてください。
    # ジョークを交えた大阪弁で面白おかしく、スーパーハイテンションで回答します。
    """

def is_image_request(prompt):
    """
    ユーザーの入力が画像生成の指示かどうかを判定
    """
    keywords = ["絵を描いて", "イラストを作って", "画像を生成", "写真を作成", "描いて"]
    return any(keyword in prompt for keyword in keywords)

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
    sanitized = re.sub(r'[\\/*?:"<>|]', '', sanitized)
    
    # スペースをアンダースコアに置換
    sanitized = sanitized.replace(' ', '_')
    
    # 先頭と末尾の空白と句読点を削除
    sanitized = sanitized.strip(' 　.,。、')
    
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
    images_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "generated_images")
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

def chat_with_gpt(prompt):
    """
    OpenAI API にテキストを送信し、GPT-4oの応答を取得
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content  # GPT-4o の応答を取得

def handle_request(prompt):
    """
    入力に応じて、画像生成かテキスト応答を選択し処理する
    """
    if is_image_request(prompt):
        print("画像生成モード: DALL·E を使用")
        image_url = generate_image(prompt)
        image = download_and_resize_image(image_url)
        # 画像を保存
        save_image(image, prompt)
        return {"type": "image", "image": image}
    else:
        print("テキスト応答モード: GPT-4o-mini を使用")
        response = chat_with_gpt(prompt)
        return {"type": "text", "content": response}

if __name__ == "__main__":
    print("音声入力を受け付けます（終了するには 'exit' と入力）")

    while True:
        user_input = input("あなた: ")
        if user_input.lower() == "exit":
            print("終了します。")
            break
        
        response = handle_request(user_input)
        if response["type"] == "image":
            # epd_display.display_image関数を使用
            epd_display.display_image(response["image"])
            print("画像を電子ペーパーに表示しました！")
        else:
            epd_display.display_text(response["content"])
            print("テキストを電子ペーパーに表示しました！")
