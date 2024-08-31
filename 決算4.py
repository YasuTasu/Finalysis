import streamlit as st
from PIL import Image
import openai
import io  # io モジュールをインポート
import fitz  # PyMuPDFをインポート
import base64
import requests

# ローカルのPNG画像を読み込む関数
def get_base64_of_bin_file(bin_file):
    data = bin_file.read()
    return base64.b64encode(data).decode()

# ここで、背景にしたい画像のパスを指定します
img_file_path = '2024-08-25 1300.png'

# 画像をBase64にエンコード
try:
    with open(img_file_path, 'rb') as img_file:
        img_base64 = get_base64_of_bin_file(img_file)
except FileNotFoundError:
    st.error("指定された背景画像ファイルが見つかりません。")
    img_base64 = ''

# CSSで背景画像を設定
page_bg_img = f'''
<style>
.stApp {{
    background-image: url("data:image/png;base64,{img_base64}");
    background-size: cover;
    background-repeat: no-repeat;
    background-attachment: fixed;
    background-position: center;
}}
</style>
'''

st.markdown(page_bg_img, unsafe_allow_html=True)

# カスタムCSSを追加
st.markdown("""
<style>
.stDownloadButton > button {
    background-color: #FFD700;
    color: white;
    border-radius: 5px;
    padding: 8px 16px;
    font-size: 16px;
    border: none;
    margin-bottom: 60px;
}
.stDownloadButton > button:hover {
    background-color: #FFFF00;
}
</style>
""", unsafe_allow_html=True)

# OCR.space APIのキーとエンドポイント
try:
    OCR_SPACE_API_KEY = st.secrets["ocr_space"]["api_key"]
    OCR_SPACE_API_URL = "https://api.ocr.space/parse/image"
except KeyError:
    st.error("OCR.spaceのAPIキーが設定されていません。Streamlit CloudのSecrets設定を確認してください。")
    OCR_SPACE_API_KEY = ""
    OCR_SPACE_API_URL = ""

# OCRを行う関数
def ocr_image(image_file):
    if not OCR_SPACE_API_KEY:
        return "OCR.space APIキーが設定されていません。"
    
    response = requests.post(
        OCR_SPACE_API_URL,
        files={"file": image_file},
        data={"apikey": OCR_SPACE_API_KEY}
    )
    result = response.json()
    return result.get('ParsedResults', [{}])[0].get('ParsedText', '')

# 画像読み込みのための言語と言語のコードを変換するリストを設定
set_language_list = {
    "日本語": "jpn",
    "英語": "eng",
}

# 選択肢を作成
prompt_option_list = {
    "重要なポイントを要約": "決算資料の内容を分析し、重要なポイントを要約してください。",
    "売上高と利益率の変動要因": "決算資料に基づいて、売上高と営業利益率の変動要因を分析してください。特に、前年同期比での変化に注目し、外部環境や内部施策がどのように影響したかを詳しく説明してください。",
    "セグメント別業績の評価": "決算資料のセグメント別の業績を分析してください。各セグメントの売上高や営業利益がどのように推移したのか、その主な要因を説明してください。また、セグメント間の成長性の違いについても考察してください。",
    "財務健全性の評価": "決算資料に基づいて、企業の財務健全性を評価してください。特に、自己資本比率、負債比率、キャッシュフローの状況などに注目し、企業の財政状態がどのように変化したかを分析してください。",
    "利益配分の戦略": "決算資料から、企業の利益配分戦略について分析してください。配当金の支払い方針や自社株買いの実施状況を考慮し、企業が株主還元にどのような姿勢を取っているのか、またその背景を考察してください。",
    "今後の市場トレンドを予測": "この資料に基づいて今後の市場トレンドを予測してください。"
}

# APIキーの設定
openai.api_key = st.secrets["openai"]["api_key"]

# OpenAIクライアントのインスタンスを作成する
client = openai.OpenAI(api_key=openai.api_key)

# Streamlit アプリケーションの開始
st.title("決算資料分析アプリ")

# ファイルアップロードのセクション
st.header("ファイルアップロード")
file_type = st.selectbox("ファイルの種類を選んでください。", ["画像ファイル", "PDFファイル"])

if file_type == "画像ファイル":
    file_upload = st.file_uploader("ここに決算資料の画像ファイルをアップロードしてください。", type=["png", "jpg"])
    
    if file_upload is not None:
        # PIL.Imageに変換
        image = Image.open(io.BytesIO(file_upload.read()))
        st.image(image, caption='アップロードされた画像', use_column_width=True)
        # OCRを実行
        txt = ocr_image(file_upload)
        
        # 抽出されたテキストを隠すためにst.expanderを使用
        with st.expander("抽出されたテキスト", expanded=False):
            st.write(txt)

        # プロンプト選択のための選択肢を表示
        selected_prompt = st.selectbox("分析の種類を選んでください。", list(prompt_option_list.keys()))
        prompt = prompt_option_list[selected_prompt]

        # GPTに分析させる
        st.write("分析結果:")
        gpt_prompt = f"{prompt}\n\n以下の決算資料の内容を分析してください:\n\n{txt[:3000]}"  # テキストを3000文字以内に制限
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "user", "content": gpt_prompt},
                ],
                max_tokens=1000  # トークン数を増やす
            )

            analysis = response.choices[0].message.content.strip()
            st.write(analysis)
            
            # 生成された分析結果をダウンロードするボタンを設置
            st.download_button(label='分析結果をダウンロード', data=analysis, file_name='analysis.txt', mime='text/plain')
        
        except openai.PermissionDeniedError as e:
            st.error(f"APIリクエストでエラーが発生しました: {e}")

elif file_type == "PDFファイル":
    file_upload = st.file_uploader("ここに決算資料のPDFファイルをアップロードしてください。", type=["pdf"])

    if file_upload is not None:
        doc = fitz.open(stream=file_upload.read(), filetype="pdf")
        text = ""
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text += page.get_text()

        # 抽出されたテキストを隠すためにst.expanderを使用
        with st.expander("抽出されたテキスト", expanded=False):
            st.write(text)

        # プロンプト選択のための選択肢を表示
        selected_prompt = st.selectbox("分析の種類を選んでください。", list(prompt_option_list.keys()))
        prompt = prompt_option_list[selected_prompt]

        # GPTに分析させる
        st.write("分析結果:")
        gpt_prompt = f"{prompt}\n\n以下の決算資料の内容を分析してください:\n\n{text[:3000]}"  # テキストを3000文字以内に制限
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "user", "content": gpt_prompt},
                ],
                max_tokens=1000  # トークン数を増やす
            )

            analysis = response.choices[0].message.content.strip()
            st.write(analysis)
            
            # 生成された分析結果をダウンロードするボタンを設置
            st.download_button(label='分析結果をダウンロード', data=analysis, file_name='analysis.txt', mime='text/plain')
        
        except openai.PermissionDeniedError as e:
            st.error(f"APIリクエストでエラーが発生しました: {e}")
