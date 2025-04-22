from flask import Flask, request, render_template_string, redirect, url_for
import subprocess
import os
import tempfile
import sys # Add missing import

app = Flask(__name__)

# 一時ファイルのパスを定義
TRIGGER_FILE_PATH = os.path.join(tempfile.gettempdir(), "conversation_starter.txt")

# HTMLテンプレート
HTML_TEMPLATE = """
<!doctype html>
<html lang="ja">
<head>
    <meta charset="utf-8">
    <title>会話開始トリガー</title>
    <style>
        body { font-family: sans-serif; margin: 20px; }
        textarea { width: 80%; min-height: 100px; margin-bottom: 10px; padding: 8px; }
        button { padding: 10px 20px; font-size: 16px; }
        .message { margin-top: 20px; padding: 10px; border: 1px solid green; background-color: #e8f5e9; }
    </style>
</head>
<body>
    <h1>最初の会話内容を入力してください</h1>
    <form action="{{ url_for('start_conversation') }}" method="post">
        <textarea name="initial_text" placeholder="ここに話しかけたい内容を入力..." required></textarea><br>
        <button type="submit">会話を開始</button>
    </form>
    {% if message %}
        <div class="message">{{ message }}</div>
    {% endif %}
</body>
</html>
"""

@app.route('/', methods=['GET'])
def index():
    """入力フォームを表示"""
    # 既存のトリガーファイルがあれば削除しておく
    if os.path.exists(TRIGGER_FILE_PATH):
        try:
            os.remove(TRIGGER_FILE_PATH)
            print(f"既存のトリガーファイルを削除しました: {TRIGGER_FILE_PATH}")
        except OSError as e:
            print(f"既存トリガーファイルの削除に失敗: {e}")
    return render_template_string(HTML_TEMPLATE)

@app.route('/start_conversation', methods=['POST'])
def start_conversation():
    """テキストを受け取り、一時ファイルに保存し、main.pyを起動"""
    initial_text = request.form.get('initial_text')
    message = None

    if not initial_text:
        message = "テキストが入力されていません。"
        return render_template_string(HTML_TEMPLATE, message=message), 400

    try:
        # テキストを一時ファイルに書き込む
        with open(TRIGGER_FILE_PATH, 'w', encoding='utf-8') as f:
            f.write(initial_text)
        print(f"トリガーファイルを作成しました: {TRIGGER_FILE_PATH} 内容: '{initial_text[:50]}...'")

        # main.py のパスを取得 (web_trigger.py と同じディレクトリにあると仮定)
        main_py_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
        python_executable = os.path.join(os.path.dirname(sys.executable), 'python') # venv内のpythonを使う

        # main.py を非同期で実行 (Popenを使い、完了を待たない)
        # 注意: main.py が適切な環境変数(APIキーなど)を読み込めるように実行する必要がある
        #       venv環境で実行する場合、そのPythonインタプリタを指定する
        print(f"Executing: {python_executable} {main_py_path}")
        process = subprocess.Popen([python_executable, main_py_path])
        print(f"main.py をプロセスID {process.pid} で起動しました。")

        message = "会話を開始しました！ スピーカーからの応答をお待ちください。"

    except Exception as e:
        print(f"エラーが発生しました: {e}")
        message = f"エラーが発生しました: {e}"
        # エラー発生時はトリガーファイルを削除しておく
        if os.path.exists(TRIGGER_FILE_PATH):
            try:
                os.remove(TRIGGER_FILE_PATH)
            except OSError:
                pass
        return render_template_string(HTML_TEMPLATE, message=message), 500

    # 成功メッセージを表示しつつ、フォームを再度表示
    # redirectを使うとメッセージが表示できないため、render_template_stringを使う
    return render_template_string(HTML_TEMPLATE, message=message)

if __name__ == '__main__':
    # 0.0.0.0 でリッスンし、ポート5002を使用 (web_app.pyと衝突しないように)
    app.run(debug=True, host='0.0.0.0', port=5002)
