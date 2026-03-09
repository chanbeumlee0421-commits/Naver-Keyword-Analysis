import streamlit as st
import requests
import pandas as pd
from konlpy.tag import Okt
from collections import Counter
import datetime

# 1. 페이지 설정
st.set_page_config(page_title="네이버 여론 분석 대시보드", layout="wide")

# 2. API 키 자동 로드 (Secrets 우선, 없으면 사이드바)
naver_id = st.secrets.get("NAVER_CLIENT_ID", "")
naver_secret = st.secrets.get("NAVER_CLIENT_SECRET", "")

if not naver_id:
    with st.sidebar:
        st.header("🔑 API 설정")
        naver_id = st.text_input("Naver Client ID", type="password")
        naver_secret = st.text_input("Naver Client Secret", type="password")

# 3. 사이드바 - 검색 옵션 (기간 및 출처)
with st.sidebar:
    st.header("⚙️ 검색 설정")
    source_type = st.radio("출처 선택", ["블로그", "카페"])
    source_api = "blog" if source_type == "블로그" else "cafearticle"
    
    today = datetime.date.today()
    start_date = st.date_input("시작일", today - datetime.timedelta(days=30))
    end_date = st.date_input("종료일", today)
    
    display_num = st.slider("수집 개수", 10, 100, 50)

# 4. 메인 화면
st.title(f"🔍 '{source_type}' 여론 상세 분석")
target_keyword = st.text_input("분석 키워드", value="티스템")

if st.button("데이터 분석 시작 🚀"):
    if not naver_id or not naver_secret:
        st.error("API 키를 설정해주세요.")
    else:
        with st.spinner('네이버 데이터를 분석 중입니다...'):
            url = f"https://openapi.naver.com/v1/search/{source_api}?query={target_keyword}&display={display_num}&sort=sim"
            headers = {"X-Naver-Client-Id": naver_id, "X-Naver-Client-Secret": naver_secret}
            res = requests.get(url, headers=headers)

            if res.status_code == 200:
                items = res.json().get('items', [])
                if items:
                    df = pd.DataFrame(items)
                    # 데이터 정제
                    df['clean_desc'] = df['description'].str.replace('<b>','').str.replace('</b>','').str.replace('&quot;','')
                    all_text = " ".join(df['clean_desc'].tolist())
                    
                    # 형태소 분석
                    okt = Okt()
                    nouns = [n for n in okt.nouns(all_text) if len(n) > 1 and n != target_keyword]
                    
                    # 분석 데이터 1: 연관어 Top 10
                    top_nouns = Counter(nouns).most_common(10)
                    
                    # 분석 데이터 2: 긍/부정어 순위 (사전 확장)
                    pos_dict = ['효과', '추천', '만족', '성공', '좋은', '개선', '강추', '도움', '혁신', '정상']
                    neg_dict = ['부작용', '비싼', '부담', '실패', '아쉬운', '통증', '주의', '논란', '힘든', '어려운']
                    
                    pos_found = [w for w in okt.morphs(all_text) if w in pos_dict]
                    neg_found = [w for w in okt.morphs(all_text) if w in neg_dict]
                    
                    top_pos = Counter(pos_found).most_common(10)
                    top_neg = Counter(neg_found).most_common(10)

                    # --- 결과 화면 배치 ---
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.subheader("🔝 주요 연관어 Top 10")
                        if top_nouns:
                            res_df = pd.DataFrame(top_nouns, columns=['키워드', '빈도'])
                            st.table(res_df)
                        else:
                            st.write("데이터 부족")

                    with col2:
                        st.subheader("😊 긍정어 순위")
                        if top_pos:
                            st.table(pd.DataFrame(top_pos, columns=['단어', '빈도']))
                        else:
                            st.write("긍정 키워드 없음")

                    with col3:
                        st.subheader("😟 부정어 순위")
                        if top_neg:
                            st.table(pd.DataFrame(top_neg, columns=['단어', '빈도']))
                        else:
                            st.write("부정 키워드 없음")

                    st.markdown("---")
                    st.subheader(f"🌐 {source_type} 원문 데이터 (기간: {start_date} ~ {end_date})")
                    st.dataframe(df[['title', 'link', 'clean_desc']].rename(columns={'clean_desc': '요약 내용'}))
                else:
                    st.error("검색 결과가 없습니다.")
            else:
                st.error(f"API 호출 실패: {res.status_code}")
