import streamlit as st
import requests
import pandas as pd
from konlpy.tag import Okt
from collections import Counter
import urllib.parse
import os
import time
import datetime
import matplotlib.pyplot as plt
from wordcloud import WordCloud

# 1. 페이지 설정
st.set_page_config(page_title="경보제약 네이버 여론 분석기", layout="wide")

def get_font_path():
    paths = ['NanumGothic.ttf', '/usr/share/fonts/truetype/nanum/NanumGothic.ttf']
    for p in paths:
        if os.path.exists(p): return p
    return None

# 2. API 로드
naver_id = st.secrets.get("NAVER_CLIENT_ID", "")
naver_secret = st.secrets.get("NAVER_CLIENT_SECRET", "")

# 3. 사이드바 설정
with st.sidebar:
    st.header("⚙️ 분석 설정")
    search_option = st.radio("데이터 출처", ["블로그만", "카페만", "통합 분석"])
    
    st.markdown("---")
    st.subheader("📅 분석 기간 설정")
    today = datetime.date.today()
    start_date = st.date_input("시작일", today - datetime.timedelta(days=30))
    end_date = st.date_input("종료일", today)
    
    # [핵심] 일자별 트렌드를 위해 '최신순'을 기본값으로 강제 설정
    st.info("💡 일자별 트렌드를 정확히 보기 위해 '최신순' 수집을 권장합니다.")
    sort_type = st.selectbox("수집 정렬 방식", ["date", "sim"], format_func=lambda x: "최신순(date) - 트렌드 분석용" if x=="date" else "유사도순(sim) - 인기글 위주")

st.title("🏥 경보제약 네이버 여론 분석기")

# 4. 검색 필터
c_k1, c_k2, c_k3 = st.columns([2, 1, 1])
with c_k1:
    target_keyword = st.text_input("🔍 분석 키워드 입력", value="티스템")
with c_k2:
    must_include = st.text_input("📌 필수 포함 단어", placeholder="예: 무릎")
with c_k3:
    exclude_words = st.text_input("🚫 제외 단어", placeholder="쉼표 구분")

if 'df' not in st.session_state:
    st.session_state.df = None

if st.button("분석 시작 (5,000건 고속 수집) 🚀"):
    all_items = []
    api_list = ["blog"] if "블로그" in search_option else ["cafearticle"] if "카페" in search_option else ["blog", "cafearticle"]
    
    # 5,000개 수집을 위한 키워드 확장
    sub_keywords = ["", " 효과", " 후기", " 가격", " 추천", " 부작용"]

    with st.spinner('날짜별 데이터를 골고루 수집하는 중입니다...'):
        for api_type in api_list:
            for sub in sub_keywords:
                search_query = target_keyword + sub
                # 1000개씩 루프 (총 5~6000개 시도)
                for i in range(0, 1000, 100):
                    start_num = i + 1
                    query = urllib.parse.quote(search_query)
                    url = f"https://openapi.naver.com/v1/search/{api_type}?query={query}&display=100&start={start_num}&sort={sort_type}"
                    headers = {"X-Naver-Client-Id": naver_id, "X-Naver-Client-Secret": naver_secret}
                    
                    try:
                        res = requests.get(url, headers=headers)
                        if res.status_code == 200:
                            items = res.json().get('items', [])
                            if not items: break
                            for item in items:
                                clean_desc = item['description'].replace('<b>','').replace('</b>','').replace('&quot;','')
                                if must_include and must_include not in (item['title'] + clean_desc): continue
                                
                                p_date = pd.to_datetime(item.get('postdate', today.strftime('%Y%m%d')), format='%Y%m%d', errors='coerce').date()
                                
                                if start_date <= p_date <= end_date:
                                    all_items.append({'source': "블로그" if api_type == "blog" else "카페", 'date': p_date, 'title': item['title'], 'link': item['link'], 'clean_desc': clean_desc})
                        else: break
                    except: break
                    # 속도를 위해 대기 시간 제거 (API 제한 범위 내)
        
        if all_items:
            st.session_state.df = pd.DataFrame(all_items).drop_duplicates(subset=['link'])
        else:
            st.warning("데이터가 없습니다. 기간을 넓혀보세요.")

if st.session_state.df is not None:
    df = st.session_state.df
    
    # 상단 지표
    m1, m2, m3 = st.columns(3)
    m1.metric("분석 대상 데이터", f"{len(df)} 건")
    m2.metric("블로그 소스", f"{len(df[df['source']=='블로그'])} 건")
    m3.metric("카페 소스", f"{len(df[df['source']=='카페'])} 건")

    # [핵심] 일자별 트렌드 보정
    st.subheader("📈 일자별 게시/관심 트렌드")
    df['date'] = pd.to_datetime(df['date'])
    # 선택한 날짜 범위 전체를 생성하여 빈 날짜도 0으로 채움
    date_index = pd.date_range(start=start_date, end=end_date)
    trend_data = df.groupby('date').size().reindex(date_index, fill_value=0)
    st.line_chart(trend_data)

    # 키워드 분석
    okt = Okt()
    full_text = " ".join(df['clean_desc'].tolist())
    # 단어 보정 (티스 -> 티스템)
    raw_nouns = okt.nouns(full_text)
    prefix = target_keyword[:2]
    processed_nouns = [target_keyword if n == prefix else n for n in raw_nouns if len(n) > 1 and n != target_keyword]
    counts = Counter(processed_nouns)

    # 시각화 레이아웃
    col_wc, col_table = st.columns([1.5, 1])
    with col_wc:
        st.subheader("☁️ 키워드 시각화")
        f_path = get_font_path()
        if f_path and processed_nouns:
            wc = WordCloud(font_path=f_path, background_color='white', width=800, height=450, colormap='GnBu').generate_from_frequencies(counts)
            fig, ax = plt.subplots(figsize=(10, 5)); ax.imshow(wc); ax.axis('off'); st.pyplot(fig)
    
    with col_table:
        st.subheader("🔝 TOP 15 키워드")
        st.table(pd.DataFrame(counts.most_common(15), columns=['단어', '빈도']))

    # 원문 필터링
    st.markdown("---")
    st.subheader("🔍 키워드별 원문 상세보기")
    selected_word = st.selectbox("분석하고 싶은 키워드 선택", ["전체 보기"] + [word for word, count in counts.most_common(50)])
    filter_df = df if selected_word == "전체 보기" else df[df['clean_desc'].str.contains(selected_word) | df['title'].str.contains(selected_word)]
    st.dataframe(filter_df[['source', 'date', 'title', 'link', 'clean_desc']])
