import streamlit as st
import requests
import pandas as pd
from konlpy.tag import Okt
from collections import Counter
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import os

# 1. 한글 폰트 경로 설정 함수
def get_font_path():
    # 깃허브에 함께 올린 폰트 파일 확인
    local_font = 'NanumGothic.ttf'
    if os.path.exists(local_font):
        return local_font
    
    # 리눅스 서버 기본 폰트 경로 확인 (Streamlit Cloud용)
    linux_font = '/usr/share/fonts/truetype/nanum/NanumGothic.ttf'
    if os.path.exists(linux_font):
        return linux_font
    
    return None

st.set_page_config(page_title="네이버 키워드 분석기", layout="wide")

# ... (중략: API 설정 및 데이터 수집 로직) ...

# 2. 워드클라우드 생성 부분 수정
with col1:
    st.subheader("📌 주요 키워드")
    if nouns:
        word_counts = Counter(nouns)
        font_path = get_font_path() # 설정한 폰트 경로 가져오기
        
        if font_path:
            wc = WordCloud(
                font_path=font_path, 
                background_color='white', 
                width=800, 
                height=500
            ).generate_from_frequencies(word_counts)
            
            fig_wc, ax_wc = plt.subplots()
            ax_wc.imshow(wc, interpolation='bilinear')
            ax_wc.axis('off')
            st.pyplot(fig_wc)
        else:
            st.error("한글 폰트 파일(NanumGothic.ttf)을 찾을 수 없습니다. 깃허브에 폰트 파일을 올려주세요.")
