import openai  # OpenAI API クライアント
import os  # 環境変数取得用

# OpenAI API キーを環境変数から取得
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("環境変数 'OPENAI_API_KEY' が設定されていません！")

# OpenAI クライアントを作成
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# 事前設定（システムメッセージ）
SYSTEM_PROMPT = \
    """
    # あなたは知識豊富な大阪在住の気のいいおばさんです。大阪弁で回答します。
    # 簡潔かつわかりやすく回答してください。
    """
    
def chat_with_gpt(prompt):
    """
    OpenAI API にテキストを送信し、GPT-4oの応答を取得する（最新の API 仕様）。
    """
    response = client.chat.completions.create(
        model="gpt-4o",  # GPT-4 を指定
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},  # 事前設定（システムメッセージ）
            {"role": "user", "content": prompt}  # ユーザーの入力
        ]
    )
    return response.choices[0].message.content  # GPT-4 の応答を取得

if __name__ == "__main__":
    user_input = input("質問を入力してください: ")  # ユーザー入力
    response = chat_with_gpt(user_input)
    print("GPT-4の応答:", response)
