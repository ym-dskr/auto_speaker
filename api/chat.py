import os
import openai
import requests
from io import BytesIO
from PIL import Image
from display import epd_display
import datetime
import re
from tavily import TavilyClient
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

# OpenAI APIキーを環境変数から取得
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

if not TAVILY_API_KEY:
    raise ValueError("環境変数 'TAVILY_API_KEY' が設定されていません！")
    
tavily_client = TavilyClient(api_key=TAVILY_API_KEY)

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


def sanitize_filename(text, max_length=500):
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
    # 1. プロンプトが最新情報を求めているかどうかを判断
    needs_latest_info = check_if_needs_latest_info(prompt)
    
    # 最新情報が必要な場合のみTavily APIを使用
    if needs_latest_info:
        # Tavily APIを使用して、プロンプトに関連する最新情報を検索（include_answer=Trueを追加）
        search_results = tavily_client.search(prompt, history=history, include_answer=True)

        # answerからtitles_textを作成
        titles_text = ""
        if isinstance(search_results, dict) and 'answer' in search_results and search_results['answer']:
            titles_text = search_results['answer']
        else:
            # フォールバック: answerがない場合は従来通りresultsから作成
            titles = []
            if isinstance(search_results, dict) and 'results' in search_results:
                for result in search_results['results']:
                    if 'content' in result:
                        titles.append(result['content'])
            
            # タイトルのリストを文字列に変換
            titles_text = "\n- ".join(titles)
            if titles:
                titles_text = "- " + titles_text

        # 検索結果をプロンプトに追加
        prompt_with_context = f"{prompt}\n\n以下の関連情報を参考にして,なるべく要約せず具体的な回答をしてください:\n{titles_text}\n\n詳細情報:\n{search_results}"
        print(f"最新情報が必要と判断しました。検索結果タイトル:\n{titles_text}")
    else:
        # 最新情報が不要な場合は元のプロンプトをそのまま使用
        prompt_with_context = prompt
        print("最新情報は不要と判断しました。Tavily APIは使用しません。")

    # 3. 会話履歴にユーザーのプロンプトを追加
    # システムプロンプトが含まれていない場合は追加する
    if not history or history[0].get("role") != "system":
        current_history = [{"role": "system", "content": SYSTEM_PROMPT}] + history + [{"role": "user", "content": prompt_with_context}]
    else:
        current_history = history + [{"role": "user", "content": prompt_with_context}]

    # 4. ユーザーのプロンプトに対する応答を取得 (会話履歴全体を渡す)
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

def summarize_text_for_display(text, max_chars=500):
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


def generate_greeting():
    """
    起動時の挨拶をGPTに生成させる
    """
    greeting_prompt = """
    これからユーザーが話しかけてきます。
    あなたのキャラクター設定（SYSTEM_PROMPT）に従って、元気の良い大阪弁で、何か気の利いた一言挨拶を生成してください。
    短く簡潔にお願いします。
    例：「まいど！」「なんか用か？」「元気にしてたか？」
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT}, # 既存のシステムプロンプトを活用
                {"role": "user", "content": greeting_prompt}
            ],
            max_tokens=50 # 短い挨拶を期待
        )
        greeting = response.choices[0].message.content.strip()
        # 念のため、空でないか確認
        if not greeting:
            greeting = "まいど！なんか用か？" # デフォルトの挨拶
        return greeting
    except Exception as e:
        print(f"挨拶生成中にエラーが発生しました: {e}")
        return "まいど！なんか用か？" # エラー時のデフォルト挨拶

def generate_farewell():
    """
    終了時の応答をGPTに生成させる
    """
    farewell_prompt = """
    ユーザーがもう話すことがないようです。
    あなたのキャラクター設定（SYSTEM_PROMPT）に従って、元気の良い大阪弁で、何か気の利いた別れの挨拶を生成してください。
    短く簡潔にお願いします。
    例：「ほな、またな！」「さいなら！」「なんかあったらまた呼んでや！」
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT}, # 既存のシステムプロンプトを活用
                {"role": "user", "content": farewell_prompt}
            ],
            max_tokens=50 # 短い挨拶を期待
        )
        farewell = response.choices[0].message.content.strip()
        # 念のため、空でないか確認
        if not farewell:
            farewell = "ほな、またな！" # デフォルトの挨拶
        return farewell
    except Exception as e:
        print(f"別れの挨拶生成中にエラーが発生しました: {e}")
        
        
def check_if_needs_latest_info(prompt):
    """
    ユーザーのプロンプトが最新情報を求めているかどうかを判断する
    """
    check_prompt = f"""
    以下のユーザーの質問やプロンプトが、最新のニュース、時事問題、最近の出来事、現在の状況など、
    最新の情報を必要としているかどうかを判断してください。
    >
    例えば、以下のようなプロンプトは最新情報が必要です：
    - 「今日のニュースは？」
    - 「最近の株価はどうなっている？」
    - 「現在の天気はどう？」
    - 「今年のオリンピックの結果は？」
    - 「最新のスマホの特徴は？」
    
    一方、以下のようなプロンプトは一般的な知識で回答可能で、最新情報は不要です：
    - 「水の沸点は？」
    - 「犬の種類を教えて」
    - 「数学の問題を解いて」
    - 「昔話を聞かせて」
    - 「歴史上の人物について教えて」
    
    ユーザープロンプト: {prompt}
    
    このプロンプトは最新情報を必要としていますか？「はい」か「いいえ」だけで答えてください。
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたはユーザーの質問が最新情報を必要としているかどうかを判断するAIです。"},
                {"role": "user", "content": check_prompt}
            ],
            max_tokens=5  # 「はい」か「いいえ」だけを期待
        )
        result = response.choices[0].message.content.strip().lower()
        
        # 「はい」が含まれていれば最新情報が必要と判断
        return "はい" in result or "yes" in result
    except Exception as e:
        print(f"最新情報の必要性判断中にエラーが発生しました: {e}")
        # エラーの場合は安全側に倒して最新情報を取得する
        return True


if __name__ == "__main__":
    # テスト用: 挨拶を生成して表示
    # print(generate_greeting())
    # print(generate_farewell()) # テスト用に追加
    pass # mainブロックは特に何もしないように変更
