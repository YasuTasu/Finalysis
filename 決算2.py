import streamlit as st
import openai
import os
import fitz  # PyMuPDF
import pytesseract
import platform
import base64

# ローカルのPNG画像を読み込む関数
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

# ここで、背景にしたい画像のパスを指定します
img_file_path = '2024-08-25 1300.png'

# 画像をBase64にエンコード
img_base64 = get_base64_of_bin_file(img_file_path)

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

# Tesseractのパスを指定 (Windows用)
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'

# OCRエンジンの設定
def ocr_image(image_path, lang='jpn'):
    return pytesseract.image_to_string(image_path, lang=lang)

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
api_key = st.secrets['openai']['api_key']

# Streamlit アプリケーションの開始
st.title("決算資料分析アプリ")

# ファイルアップロードのセクション
st.header("ファイルアップロード")
file_type = st.selectbox("ファイルの種類を選んでください。", ["画像ファイル", "PDFファイル"])

if file_type == "画像ファイル":
    file_upload = st.file_uploader("ここに決算資料の画像ファイルをアップロードしてください。", type=["png", "jpg"])
    
    if file_upload is not None:
        st.image(file_upload)
        selected_language = st.selectbox("文字認識する言語を選んでください。", list(set_language_list.keys()))
        txt = ocr_image(file_upload, lang=set_language_list[selected_language])
        
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
            response = openai.chat.completions.create(
                model="gpt-4-turbo",  # 使用するモデルを指定
                messages=[
                    {"role": "user", "content": gpt_prompt},
                ],
                max_tokens=1000
            )
            
            analysis = response.choices[0].message["content"].strip()
            st.write(analysis)
            
            # 生成された分析結果をダウンロードするボタンを設置
            st.download_button(label='分析結果をダウンロード', data=analysis, file_name='analysis.txt', mime='text/plain')
        
        except openai.OpenAIError as e:
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
            response = openai.ChatCompletion.create(
                model="gpt-4-turbo",  # 使用するモデルを指定
                messages=[
                    {"role": "user", "content": gpt_prompt},
                ],
                max_tokens=1000
            )
            
            analysis = response.choices[0].message["content"].strip()
            st.write(analysis)
            
            # 生成された分析結果をダウンロードするボタンを設置
            st.download_button(label='分析結果をダウンロード', data=analysis, file_name='analysis.txt', mime='text/plain')
        
        except openai.OpenAIError as e:
            st.error(f"APIリクエストでエラーが発生しました: {e}")
