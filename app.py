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
    if not naver_id:
        naver_id = st.text_input("Naver Client ID", type="password")
        naver_secret = st.text_input("Naver Client Secret", type="password")
    
    st.markdown("---")
    st.subheader("📅 분석 기간 및 출처")
    search_option = st.radio("데이터 출처", ["블로그만", "카페만", "통합 분석"])
    
    today = datetime.date.today()
    start_date = st.date_input("시작일", today - datetime.timedelta(days=30))
    end_date = st.date_input("종료일", today)
    
    collection_mode = st.selectbox("수집 강도 설정", ["표준 분석 (1000건)", "심층 분석 (최대 5000건)"])
    st.info("설정한 기간 내에 발행된 데이터만 최종 결과에 포함됩니다.")

st.title("🏥 경보제약 네이버 여론 분석기")

# 4. 검색 필터부
c_k1, c_k2, c_k3 = st.columns([2, 1, 1])
with c_k1:
    target_keyword = st.text_input("🔍 분석 키워드 입력", value="티스템")
with c_k2:
    must_include = st.text_input("📌 필수 포함 단어", placeholder="예: 무릎")
with c_k3:
    exclude_words = st.text_input("🚫 제외 단어", placeholder="쉼표로 구분")

if st.button("실시간 여론 분석 및 트렌드 리포트 생성 🚀"):
    if not naver_id or not naver_secret:
        st.error("API 키를 설정해주세요 (Streamlit Secrets 또는 사이드바)")
    else:
        all_items = []
        api_list = ["blog"] if "블로그" in search_option else ["cafearticle"] if "카페" in search_option else ["blog", "cafearticle"]
        # 심층 분석 모드 시 연관어 조합으로 5,000건 수집
        sub_keywords = ["", " 효과", " 후기", " 가격", " 추천", " 부작용"] if "심층" in collection_mode else [""]
        stop_words = [x.strip() for x in exclude_words.split(',')] if exclude_words else []

        with st.spinner('네이버 데이터를 수집하여 트렌드를 분석 중입니다...'):
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
                                    
                                    p_date_raw = item.get('postdate', today.strftime('%Y%m%d'))
                                    p_date = pd.to_datetime(p_date_raw, format='%Y%m%d', errors='coerce').date()
                                    
                                    # 기간 필터링
                                    if start_date <= p_date <= end_date:
                                        all_items.append({
                                            'source': "블로그" if api_type == "blog" else "카페",
                                            'date': p_date,
                                            'title': item['title'],
                                            'link': item['link'],
                                            'clean_desc': clean_desc
                                        })
                            else: break
                        except: break
                        time.sleep(0.05)

        if all_items:
            df = pd.DataFrame(all_items).drop_duplicates(subset=['link'])
            
            # --- 상단 지표 및 트렌드 ---
            m1, m2, m3 = st.columns(3)
            m1.metric("분석 대상 데이터", f"{len(df)} 건")
            m2.metric("블로그 소스", f"{len(df[df['source']=='블로그'])} 건")
            m3.metric("카페 소스", f"{len(df[df['source']=='카페'])} 건")

            st.subheader("📈 일자별 게시/관심 트렌드")
            trend_df = df.groupby('date').size().reset_index(name='count').sort_values('date')
            st.line_chart(trend_df.set_index('date'), color="#1f77b4")

            # 형태소 분석
            full_text = " ".join(df['clean_desc'].tolist())
            okt = Okt()
            raw_nouns = okt.nouns(full_text)
            
            # [지능형 보정] 검색어 파편화 방지
            prefix = target_keyword[:2]
            processed_nouns = [target_keyword if n == prefix else n for n in raw_nouns if len(n) > 1 and n != target_keyword and n not in stop_words]
            counts = Counter(processed_nouns)

            # --- 시각화 ---
            st.markdown("---")
            col_wc, col_table = st.columns([1.5, 1])
            with col_wc:
                st.subheader("☁️ 마켓 키워드 시각화")
                f_path = get_font_path()
                if f_path and processed_nouns:
                    wc = WordCloud(
                        font_path=f_path, background_color='white', 
                        width=1000, height=500, max_words=60, 
                        colormap='GnBu', prefer_horizontal=1.0, 
                        relative_scaling=0.3
                    ).generate_from_frequencies(counts)
                    fig_wc, ax_wc = plt.subplots(figsize=(10, 5))
                    ax_wc.imshow(wc, interpolation='bilinear'); ax_wc.axis('off')
                    st.pyplot(fig_wc)
            
            with col_table:
                st.subheader("🔝 TOP 15 연관어")
                st.table(pd.DataFrame(counts.most_common(15), columns=['키워드', '빈도']))

            # 긍부정 분석
            st.markdown("---")
            c1, c2 = st.columns(2)
            pos_dict = ['효과', '추천', '만족', '성공', '좋은', '개선', '도움', '완화', '정상']
            neg_dict = ['부작용', '비싼', '부담', '실패', '아쉬운', '통증', '재발', '걱정']
            
            with c1:
                st.subheader("😊 긍정 반응 순위")
                st.table(pd.DataFrame(Counter([w for w in okt.morphs(full_text) if w in pos_dict]).most_common(10), columns=['키워드', '빈도']))
            with c2:
                st.subheader("😟 부정 반응 순위")
                st.table(pd.DataFrame(Counter([w for w in okt.morphs(full_text) if w in neg_dict]).most_common(10), columns=['키워드', '빈도']))

            st.markdown("---")
            csv = df[['source', 'date', 'title', 'link', 'clean_desc']].to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 분석 데이터 CSV 다운로드", csv, f"{target_keyword}_analysis_report.csv", "text/csv")
            st.dataframe(df[['source', 'date', 'title', 'link', 'clean_desc']].rename(columns={'source':'출처', 'date':'발행일', 'clean_desc':'내용'}))
        else:
            st.warning("선택한 조건 내에 검색 결과가 없습니다. 기간을 늘리거나 제외 단어를 확인해 보세요.")
