import openai  # OpenAI API クライアント
import os  # 環境変数取得用

# OpenAI API キーを環境変数から取得
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("環境変数 'OPENAI_API_KEY' が設定されていません！")

# OpenAI クライアントを作成
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# 会話履歴を保存するリスト
conversation_history = []

# 事前設定（システムメッセージ）
SYSTEM_PROMPT = \
    """
    # あなたは知識豊富な大阪在住の気さくで世話焼きなおばちゃんです。
    # ジョークを交えた大阪弁で楽しく回答します。
    # 簡潔かつわかりやすく、具体的な回答をしてください。
    # 例を挙げる時は、3例程度を列挙してください。
    """

def chat_with_gpt(prompt):
    """
    OpenAI API にテキストを送信し、GPT-4oの応答を取得する（最新の API 仕様）。
    """
    global conversation_history

    # 会話履歴を作成
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for turn in conversation_history[-10:]:  # 最新の10ターンのみ使用
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model="gpt-4o-mini",  # GPT-4 を指定
        messages=messages
    )
    gpt_response = response.choices[0].message.content  # GPT-4 の応答を取得

    # 会話履歴を更新
    conversation_history.append({"role": "user", "content": prompt})
    conversation_history.append({"role": "assistant", "content": gpt_response})

    return gpt_response

if __name__ == "__main__":
    user_input = input("質問を入力してください: ")  # ユーザー入力
    response = chat_with_gpt(user_input)
    print("GPT-4の応答:", response)
