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

# 3. 사이드바
with st.sidebar:
    st.header("⚙️ 대량 분석 설정")
    search_option = st.radio("데이터 출처", ["블로그만", "카페만", "통합 분석"])
    collection_mode = st.selectbox("수집 모드", ["일반 (1000건)", "심층 빅데이터 (최대 5000건)"])
    st.markdown("---")
    st.info("트렌드 차트는 수집된 게시글의 발행일을 기준으로 작성됩니다.")

st.title("🏥 경보제약 네이버 여론 분석기 (Big Data Ver.)")

# 4. 검색 필터
c_k1, c_k2, c_k3 = st.columns([2, 1, 1])
with c_k1:
    target_keyword = st.text_input("🔍 분석 키워드", value="티스템")
with c_k2:
    must_include = st.text_input("📌 필수 포함", placeholder="예: 무릎")
with c_k3:
    exclude_words = st.text_input("🚫 제외 단어", placeholder="쉼표 구분")

if st.button("실시간 여론 및 트렌드 분석 시작 🚀"):
    if not naver_id or not naver_secret:
        st.error("API 키가 설정되지 않았습니다.")
    else:
        all_items = []
        api_list = ["blog"] if "블로그" in search_option else ["cafearticle"] if "카페" in search_option else ["blog", "cafearticle"]
        sub_keywords = ["", " 효과", " 후기", " 가격", " 추천", " 부작용"] if "5000" in collection_mode else [""]
        stop_words = [x.strip() for x in exclude_words.split(',')] if exclude_words else []

        progress_bar = st.progress(0)
        total_steps = len(api_list) * len(sub_keywords) * 10
        current_step = 0

        with st.spinner('대량의 데이터를 일자별로 분류하고 분석 중입니다...'):
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
                                    
                                    # 날짜 데이터 처리 (YYYYMMDD 형식으로 변환)
                                    p_date = item.get('postdate', datetime.datetime.now().strftime('%Y%m%d'))
                                    
                                    all_items.append({
                                        'source': "블로그" if api_type == "blog" else "카페",
                                        'title': item['title'],
                                        'link': item['link'],
                                        'clean_desc': clean_desc,
                                        'date': pd.to_datetime(p_date, format='%Y%m%d', errors='coerce')
                                    })
                            else: break
                        except: break
                        
                        time.sleep(0.05)
                        current_step += 1
                        progress_bar.progress(min(current_step / total_steps, 1.0))

        if all_items:
            # 중복 제거 및 데이터 프레임 생성
            df = pd.DataFrame(all_items).drop_duplicates(subset=['link'])
            df = df.dropna(subset=['date']) # 날짜 없는 데이터 제외
            
            # --- 1. 일자별 트렌드 차트 (신규 추가) ---
            st.subheader("📈 일자별 검색/게시 트렌드")
            trend_df = df.groupby(df['date'].dt.date).size().reset_index(name='count')
            trend_df = trend_df.sort_values('date')
            
            # 스트림릿 내장 라인 차트 사용 (깔끔함)
            st.line_chart(trend_df.set_index('date'))

            st.markdown("---")
            m1, m2, m3 = st.columns(3)
            m1.metric("총 유니크 데이터", f"{len(df)}건")
            m2.metric("블로그", f"{len(df[df['source']=='블로그'])}건")
            m3.metric("카페", f"{len(df[df['source']=='카페'])}건")

            # 형태소 분석 및 단어 복구
            full_text = " ".join(df['clean_desc'].tolist())
            okt = Okt()
            raw_nouns = okt.nouns(full_text)
            prefix = target_keyword[:2]
            processed_nouns = [target_keyword if n == prefix else n for n in raw_nouns if len(n) > 1 and n != target_keyword and n not in stop_words]
            counts = Counter(processed_nouns)

            # --- 2. 시각화 및 키워드 순위 ---
            st.markdown("### 📊 마켓 인사이트 요약")
            col_wc, col_table = st.columns([1.5, 1])
            
            with col_wc:
                f_path = get_font_path()
                if f_path and processed_nouns:
                    wc = WordCloud(
                        font_path=f_path,
                        background_color='white',
                        width=1000, height=500,
                        max_words=80,
                        colormap='GnBu',
                        prefer_horizontal=1.0,
                        relative_scaling=0.3
                    ).generate_from_frequencies(counts)
                    fig_wc, ax_wc = plt.subplots(figsize=(10, 5))
                    ax_wc.imshow(wc, interpolation='bilinear')
                    ax_wc.axis('off')
                    st.pyplot(fig_wc)
            
            with col_table:
                st.write("**실시간 핵심 키워드 TOP 15**")
                st.table(pd.DataFrame(counts.most_common(15), columns=['단어', '빈도']))

            # 긍부정 분석
            st.markdown("---")
            c1, c2 = st.columns(2)
            pos_dict = ['효과', '추천', '만족', '성공', '개선', '도움', '완화', '정상']
            neg_dict = ['부작용', '비싼', '부담', '실패', '아쉬운', '통증', '재발']
            
            with c1:
                st.write("✅ **긍정 여론**")
                pos_list = Counter([w for w in okt.morphs(full_text) if w in pos_dict]).most_common(10)
                st.table(pd.DataFrame(pos_list, columns=['키워드', '빈도']))
            with c2:
                st.write("❌ **부정 여론**")
                neg_list = Counter([w for w in okt.morphs(full_text) if w in neg_dict]).most_common(10)
                st.table(pd.DataFrame(neg_list, columns=['키워드', '빈도']))

            st.markdown("---")
            csv = df[['source', 'date', 'title', 'link', 'clean_desc']].to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 전체 분석 데이터 다운로드", csv, f"{target_keyword}_trend_analysis.csv", "text/csv")
            st.dataframe(df[['source', 'date', 'title', 'link', 'clean_desc']])
        else:
            st.warning("조건에 맞는 데이터가 없습니다.")
