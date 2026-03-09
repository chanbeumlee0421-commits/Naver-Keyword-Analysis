import streamlit as st
import requests
import pandas as pd
from konlpy.tag import Okt
from collections import Counter
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import platform

# 1. 페이지 설정
st.set_page_config(page_title="네이버 키워드 분석기", layout="wide")

# 한글 폰트 설정
def set_korean_font():
    if platform.system() == 'Windows':
        plt.rc('font', family='Malgun Gothic')
    elif platform.system() == 'Darwin':
        plt.rc('font', family='AppleGothic')
    else:
        plt.rc('font', family='NanumGothic')
    plt.rc('axes', unicode_minus=False)

set_korean_font()

# 2. API 키 설정 (Secrets 활용)
try:
    naver_id = st.secrets["NAVER_CLIENT_ID"]
    naver_secret = st.secrets["NAVER_CLIENT_SECRET"]
except:
    with st.sidebar:
        st.header("🔑 API 설정 (Manual)")
        naver_id = st.text_input("Naver Client ID", type="password")
        naver_secret = st.text_input("Naver Client Secret", type="password")

# 3. 메인 UI
st.title("📊 네이버 키워드 분석 대시보드")
target_keyword = st.text_input("분석할 키워드를 입력하세요", value="티스템")

if st.button("분석 시작🚀"):
    if not naver_id or not naver_secret:
        st.warning("네이버 API ID와 Secret이 설정되지 않았습니다.")
    else:
        with st.spinner('데이터를 가져와 분석 중입니다...'):
            # 네이버 검색 호출
            url = f"https://openapi.naver.com/v1/search/blog?query={target_keyword}&display=100&sort=sim"
            headers = {"X-Naver-Client-Id": naver_id, "X-Naver-Client-Secret": naver_secret}
            res = requests.get(url, headers=headers)

            if res.status_code == 200:
                items = res.json().get('items', [])
                if items:
                    df = pd.DataFrame(items)
                    df['clean_desc'] = df['description'].str.replace('<b>','').str.replace('</b>','').str.replace('&quot;','')
                    
                    # 형태소 분석
                    okt = Okt()
                    all_text = " ".join(df['clean_desc'].tolist())
                    nouns = [n for n in okt.nouns(all_text) if len(n) > 1 and n != target_keyword]
                    
                    # 시각화 영역
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader("📌 주요 키워드")
                        word_counts = Counter(nouns)
                        wc = WordCloud(font_path='NanumGothic.ttf', background_color='white', width=800, height=500).generate_from_frequencies(word_counts)
                        fig_wc, ax_wc = plt.subplots()
                        ax_wc.imshow(wc, interpolation='bilinear')
                        ax_wc.axis('off')
                        st.pyplot(fig_wc)

                    with col2:
                        st.subheader("⚖️ 긍/부정 비율")
                        # 간단 매칭 (예시 키워드)
                        pos_words = ['효과', '추천', '만족', '성공', '좋은']
                        neg_words = ['부작용', '비싼', '부담', '실패', '아쉬운']
                        pos_score = sum(all_text.count(w) for w in pos_words)
                        neg_score = sum(all_text.count(w) for w in neg_words)
                        
                        if pos_score + neg_score > 0:
                            fig_pie, ax_pie = plt.subplots()
                            ax_pie.pie([pos_score, neg_score], labels=['긍정', '부정'], autopct='%1.1f%%', colors=['#4CAF50', '#F44336'])
                            st.pyplot(fig_pie)
                        else:
                            st.write("감성 단어가 부족합니다.")
                else:
                    st.error("검색 결과가 없습니다.")
            else:
                st.error(f"API 호출 실패: {res.status_code}")
