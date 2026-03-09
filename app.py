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
    
    # 속도 개선을 위해 최대 수집 개수 조정 옵션 제공
    collection_mode = st.selectbox("수집 모드 (5000건은 시간이 소요됩니다)", ["표준 (1000건)", "고속 확장 (3000건)", "심층 빅데이터 (5000건)"])

st.title("🏥 경보제약 네이버 여론 분석기")

# 4. 검색 및 필터링 UI
c_k1, c_k2, c_k3 = st.columns([2, 1, 1])
with c_k1:
    target_keyword = st.text_input("🔍 분석 키워드 입력", value="티스템")
with c_k2:
    must_include = st.text_input("📌 필수 포함 단어", placeholder="예: 무릎")
with c_k3:
    exclude_words = st.text_input("🚫 제외 단어", placeholder="쉼표 구분")

# 세션 상태 초기화 (데이터 유지용)
if 'df' not in st.session_state:
    st.session_state.df = None

if st.button("실시간 여론 분석 시작 🚀"):
    all_items = []
    api_list = ["blog"] if "블로그" in search_option else ["cafearticle"] if "카페" in search_option else ["blog", "cafearticle"]
    
    # 수집 모드별 키워드 조합 (5000개일 때만 풀가동)
    sub_count = 1 if "표준" in collection_mode else 3 if "고속" in collection_mode else 5
    sub_keywords = ["", " 효과", " 후기", " 가격", " 추천", " 부작용"][:sub_count+1]
    stop_words = [x.strip() for x in exclude_words.split(',')] if exclude_words else []

    with st.spinner(f'최대 {len(api_list)*len(sub_keywords)*1000}건을 탐색 중입니다. 잠시만 기다려주세요...'):
        for api_type in api_list:
            for sub in sub_keywords:
                search_query = target_keyword + sub
                for i in range(0, 1000, 100):
                    start_num = i + 1
                    query = urllib.parse.quote(search_query)
                    url = f"https://openapi.naver.com/v1/search/{api_type}?query={query}&display=100&start={start_num}&sort=sim"
                    headers = {"X-Naver-Client-Id": naver_id, "X-Naver-Client-Secret": naver_secret}
                    
                    try:
                        res = requests.get(url, headers=headers)
                        if res.status_code == 200:
                            items = res.json().get('items', [])
                            if not items: break
                            for item in items:
                                clean_desc = item['description'].replace('<b>','').replace('</b>','').replace('&quot;','')
                                if must_include and must_include not in (item['title'] + clean_desc): continue
                                p_date = pd.to_datetime(item.get('postdate', '20260101'), format='%Y%m%d', errors='coerce').date()
                                if start_date <= p_date <= end_date:
                                    all_items.append({'source': "블로그" if api_type == "blog" else "카페", 'date': p_date, 'title': item['title'], 'link': item['link'], 'clean_desc': clean_desc})
                        else: break
                    except: break
                    # 속도를 위해 time.sleep 제거 또는 최소화
        
        if all_items:
            st.session_state.df = pd.DataFrame(all_items).drop_duplicates(subset=['link'])
        else:
            st.warning("데이터가 없습니다.")

# 데이터가 있을 때만 화면 출력
if st.session_state.df is not None:
    df = st.session_state.df
    
    # --- 상단 메트릭 및 트렌드 ---
    m1, m2, m3 = st.columns(3)
    m1.metric("분석 대상 데이터", f"{len(df)} 건")
    m2.metric("블로그 소스", f"{len(df[df['source']=='블로그'])} 건")
    m3.metric("카페 소스", f"{len(df[df['source']=='카페'])} 건")

    st.subheader("📈 일자별 게시/관심 트렌드")
    # 날짜 범위가 비지 않도록 재구성
    trend_df = df.groupby('date').size().reindex(pd.date_range(start_date, end_date), fill_value=0)
    st.line_chart(trend_df)

    # 형태소 분석
    okt = Okt()
    full_text = " ".join(df['clean_desc'].tolist())
    raw_nouns = okt.nouns(full_text)
    prefix = target_keyword[:2]
    processed_nouns = [target_keyword if n == prefix else n for n in raw_nouns if len(n) > 1 and n != target_keyword]
    counts = Counter(processed_nouns)

    # --- 시각화 섹션 ---
    col_wc, col_table = st.columns([1.5, 1])
    with col_wc:
        st.subheader("☁️ 키워드 시각화") # 요청대로 변경
        f_path = get_font_path()
        if f_path and processed_nouns:
            wc = WordCloud(font_path=f_path, background_color='white', width=800, height=450, colormap='GnBu', prefer_horizontal=1.0).generate_from_frequencies(counts)
            fig_wc, ax_wc = plt.subplots(figsize=(10, 5)); ax_wc.imshow(wc, interpolation='bilinear'); ax_wc.axis('off')
            st.pyplot(fig_wc)

    with col_table:
        st.subheader("🔝 TOP 15 키워드")
        st.table(pd.DataFrame(counts.most_common(15), columns=['단어', '빈도']))

    # --- [핵심 추가] 원문 필터링 기능 ---
    st.markdown("---")
    st.subheader("🔍 키워드별 원문 상세보기")
    selected_word = st.selectbox("원문을 보고 싶은 키워드를 선택하세요", ["전체 보기"] + [word for word, count in counts.most_common(50)])
    
    filter_df = df if selected_word == "전체 보기" else df[df['clean_desc'].str.contains(selected_word) | df['title'].str.contains(selected_word)]
    
    st.write(f"**'{selected_word}'** 관련 게시글: {len(filter_df)}건")
    st.dataframe(filter_df[['source', 'date', 'title', 'link', 'clean_desc']].rename(columns={'source':'출처', 'date':'발행일', 'clean_desc':'내용'}))

    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 데이터 다운로드", csv, f"{target_keyword}_analysis.csv", "text/csv")
