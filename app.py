import streamlit as st
import requests
import pandas as pd
from konlpy.tag import Okt
from collections import Counter
import urllib.parse
import os

# 1. 페이지 설정
st.set_page_config(page_title="네이버 키워드 심층 분석", layout="wide")

# 2. 한글 폰트 설정 (서버 환경 대응)
def get_font_path():
    paths = [
        'NanumGothic.ttf',
        '/usr/share/fonts/truetype/nanum/NanumGothic.ttf'
    ]
    for p in paths:
        if os.path.exists(p): return p
    return None

# 3. API 키 로드 (Secrets 사용 권장)
naver_id = st.secrets.get("NAVER_CLIENT_ID", "")
naver_secret = st.secrets.get("NAVER_CLIENT_SECRET", "")

if not naver_id:
    with st.sidebar:
        st.header("🔑 API 수동 설정")
        naver_id = st.text_input("Naver Client ID", type="password")
        naver_secret = st.text_input("Naver Client Secret", type="password")

# 4. 사이드바 검색 옵션
with st.sidebar:
    st.header("⚙️ 분석 설정")
    source = st.selectbox("데이터 출처", ["blog", "cafearticle"], format_func=lambda x: "네이버 블로그" if x=="blog" else "네이버 카페")
    num_results = st.slider("수집 데이터 수", 10, 100, 50)
    st.info("기간 설정: 네이버 API는 기본적으로 '유사도순' 정렬 시 최신 데이터를 우선 포함합니다.")

st.title("📊 네이버 키워드 여론 분석 대시보드")
target_keyword = st.text_input("분석할 키워드를 입력하세요", value="티스템")

if st.button("데이터 분석 시작 🚀"):
    if not naver_id or not naver_secret:
        st.error("API 키를 설정해주세요 (Streamlit Secrets 또는 사이드바)")
    else:
        with st.spinner('네이버 데이터를 수집하고 분석하는 중...'):
            # 한글 키워드 인코딩 처리 (UnicodeEncodeError 방지)
            encoded_keyword = urllib.parse.quote(target_keyword)
            url = f"https://openapi.naver.com/v1/search/{source}?query={encoded_keyword}&display={num_results}&sort=sim"
            headers = {"X-Naver-Client-Id": naver_id, "X-Naver-Client-Secret": naver_secret}
            
            res = requests.get(url, headers=headers)
            
            if res.status_code == 200:
                items = res.json().get('items', [])
                if items:
                    df = pd.DataFrame(items)
                    df['clean_desc'] = df['description'].str.replace('<b>','').str.replace('</b>','').str.replace('&quot;','')
                    full_text = " ".join(df['clean_desc'].tolist())
                    
                    # 형태소 분석
                    okt = Okt()
                    nouns = [n for n in okt.nouns(full_text) if len(n) > 1 and n != target_keyword]
                    
                    # 1. 연관어 Top 10
                    top_10_nouns = Counter(nouns).most_common(10)
                    
                    # 2. 긍정/부정어 매칭 및 순위 (사전 확장)
                    pos_dict = ['효과', '추천', '만족', '성공', '좋은', '개선', '강추', '도움', '혁신', '최고']
                    neg_dict = ['부작용', '비싼', '부담', '실패', '아쉬운', '통증', '주의', '논란', '힘든', '걱정']
                    
                    words = okt.morphs(full_text)
                    pos_list = [w for w in words if w in pos_dict]
                    neg_list = [w for w in words if w in neg_dict]
                    
                    top_pos = Counter(pos_list).most_common(10)
                    top_neg = Counter(neg_list).most_common(10)

                    # --- 화면 표시 ---
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.subheader("🔝 연관어 Top 10")
                        st.table(pd.DataFrame(top_10_nouns, columns=['키워드', '빈도']))
                    with c2:
                        st.subheader("😊 긍정어 순위")
                        st.table(pd.DataFrame(top_pos, columns=['단어', '빈도']))
                    with c3:
                        st.subheader("😟 부정어 순위")
                        st.table(pd.DataFrame(top_neg, columns=['단어', '빈도']))

                    st.markdown("---")
                    st.subheader(f"📋 수집된 원문 데이터 (출처: {'블로그' if source=='blog' else '카페'})")
                    st.dataframe(df[['title', 'link', 'clean_desc']].rename(columns={'clean_desc': '내용'}))
                else:
                    st.warning("검색 결과가 없습니다.")
            else:
                st.error(f"API 호출 실패: {res.status_code}")
