import streamlit as st
import requests
import pandas as pd
from konlpy.tag import Okt
from collections import Counter
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import seaborn as sns
import platform

# 1. 페이지 설정 및 한글 폰트 케어
st.set_page_config(page_title="네이버 키워드 분석기", layout="wide")

def set_korean_font():
    # 운영체제별 폰트 설정 (로컬 환경용)
    if platform.system() == 'Windows':
        plt.rc('font', family='Malgun Gothic')
    elif platform.system() == 'Darwin': # Mac
        plt.rc('font', family='AppleGothic')
    else: # 리눅스/스트림릿 클라우드
        plt.rc('font', family='NanumGothic')
    plt.rc('axes', unicode_minus=False)

set_korean_font()

# 2. 사이드바 - API 설정
with st.sidebar:
    st.header("🔑 API 설정")
    st.info("네이버 개발자 센터에서 발급받은 키를 입력하세요.")
    naver_id = st.text_input("Naver Client ID", type="password")
    naver_secret = st.text_input("Naver Client Secret", type="password")
    st.markdown("---")
    st.write("작성자: 류형도")

# 3. 메인 화면 UI
st.title("📊 네이버 키워드 여론 분석 대시보드")
st.markdown("### 검색된 블로그 내용을 바탕으로 **연관어**와 **긍/부정**을 분석합니다.")

target_keyword = st.text_input("분석할 키워드를 입력하세요", placeholder="예: 티스템, 줄기세포")

if st.button("분석 시작🚀"):
    if not naver_id or not naver_secret:
        st.warning("사이드바에서 네이버 API ID와 Secret을 먼저 입력해주세요!")
    elif not target_keyword:
        st.warning("키워드를 입력해주세요!")
    else:
        with st.spinner('네이버에서 데이터를 긁어오는 중...'):
            # 네이버 검색 API 호출
            url = f"https://openapi.naver.com/v1/search/blog?query={target_keyword}&display=100&sort=sim"
            headers = {
                "X-Naver-Client-Id": naver_id,
                "X-Naver-Client-Secret": naver_secret
            }
            res = requests.get(url, headers=headers)

            if res.status_code == 200:
                data = res.json()['items']
                if not data:
                    st.error("검색 결과가 없습니다.")
                else: