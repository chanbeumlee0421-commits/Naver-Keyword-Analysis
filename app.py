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

# 2. API 로드 및 세션 관리
naver_id = st.secrets.get("NAVER_CLIENT_ID", "")
naver_secret = st.secrets.get("NAVER_CLIENT_SECRET", "")

# 3. 사이드바
with st.sidebar:
    st.header("⚙️ 분석 설정")
    search_option = st.radio("데이터 출처", ["블로그만", "카페만", "통합 분석"])
    total_to_collect = st.select_slider("수집 개수 (출처당)", options=[100, 300, 500, 1000], value=300)
    st.markdown("---")
    st.caption("Designed for Kyongbo Pharm")

st.title("🏥 경보제약 네이버 여론 분석기")

# 4. 검색 필터 (UI 개선)
c_k1, c_k2, c_k3 = st.columns([2, 1, 1])
with c_k1:
    target_keyword = st.text_input("🔍 분석 키워드", value="티스템")
with c_k2:
    must_include = st.text_input("📌 필수 포함", placeholder="예: 무릎")
with c_k3:
    exclude_words = st.text_input("🚫 제외 단어", placeholder="쉼표로 구분")

if st.button("실시간 여론 분석 시작 🚀"):
    if not naver_id or not naver_secret:
        st.error("API 키가 설정되지 않았습니다.")
    else:
        all_items = []
        api_list = ["blog"] if "블로그" in search_option else ["cafearticle"] if "카페" in search_option else ["blog", "cafearticle"]
        stop_words = [x.strip() for x in exclude_words.split(',')] if exclude_words else []

        with st.spinner('데이터 수집 및 정제 중...'):
            for api_type in api_list:
                for i in range(0, total_to_collect, 100):
                    start_num = i + 1
                    query = urllib.parse.quote(target_keyword)
                    url = f"https://openapi.naver.com/v1/search/{api_type}?query={query}&display=100&start={start_num}&sort=sim"
                    headers = {"X-Naver-Client-Id": naver_id, "X-Naver-Client-Secret": naver_secret}
                    
                    res = requests.get(url, headers=headers)
                    if res.status_code == 200:
                        items = res.json().get('items', [])
                        if not items: break
                        for item in items:
                            clean_desc = item['description'].replace('<b>','').replace('</b>','').replace('&quot;','')
                            if must_include and must_include not in (item['title'] + clean_desc): continue
                            item['source'] = "블로그" if api_type == "blog" else "카페"
                            item['clean_desc'] = clean_desc
                            all_items.append(item)
                    time.sleep(0.1)

        if all_items:
            df = pd.DataFrame(all_items)
            
            # --- 상단 메트릭 ---
            st.markdown("---")
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Data", f"{len(df)}건")
            m2.metric("Blog", f"{len(df[df['source']=='블로그'])}건")
            m3.metric("Cafe", f"{len(df[df['source']=='카페'])}건")

            # 형태소 분석 및 단어 복구
            full_text = " ".join(df['clean_desc'].tolist())
            okt = Okt()
            raw_nouns = okt.nouns(full_text)
            
            prefix = target_keyword[:2]
            processed_nouns = [target_keyword if n == prefix else n for n in raw_nouns if len(n) > 1 and n != target_keyword and n not in stop_words]
            counts = Counter(processed_nouns)

            # --- 시각화 레이아웃 (세련된 버전) ---
            st.markdown("### 📊 마켓 트렌드 요약")
            col_wc, col_table = st.columns([1.5, 1])
            
            with col_wc:
                f_path = get_font_path()
                if f_path and processed_nouns:
                    # 세련된 컬러 테마와 폰트 배치
                    wc = WordCloud(
                        font_path=f_path,
                        background_color='white',
                        width=900, height=450,
                        max_words=50,
                        colormap='winter', # 세련된 블루/그린 톤
                        prefer_horizontal=1.0, # 가시성을 위해 가로 배치 위주
                        relative_scaling=0.4
                    ).generate_from_frequencies(counts)
                    
                    fig_wc, ax_wc = plt.subplots(figsize=(10, 5))
                    ax_wc.imshow(wc, interpolation='bilinear')
                    ax_wc.axis('off')
                    st.pyplot(fig_wc)
                else:
                    st.info("시각화할 데이터가 부족합니다.")
            
            with col_table:
                st.write("**Top Keywords**")
                st.table(pd.DataFrame(counts.most_common(12), columns=['단어', '빈도']))

            # 긍부정 분석
            st.markdown("---")
            c1, c2 = st.columns(2)
            pos_dict = ['효과', '추천', '만족', '성공', '좋은', '개선', '도움']
            neg_dict = ['부작용', '비싼', '부담', '실패', '아쉬운', '통증']
            
            with c1:
                st.write("✅ **긍정 키워드**")
                pos_list = Counter([w for w in okt.morphs(full_text) if w in pos_dict]).most_common(8)
                st.table(pd.DataFrame(pos_list, columns=['단어', '빈도']))
            with c2:
                st.write("❌ **부정 키워드**")
                neg_list = Counter([w for w in okt.morphs(full_text) if w in neg_dict]).most_common(8)
                st.table(pd.DataFrame(neg_list, columns=['단어', '빈도']))

            # 데이터 원문
            st.markdown("---")
            csv = df[['source', 'title', 'link', 'clean_desc']].to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 로우 데이터 다운로드 (CSV)", csv, f"{target_keyword}_raw.csv", "text/csv")
            st.dataframe(df[['source', 'title', 'link', 'clean_desc']].rename(columns={'source':'출처', 'clean_desc':'요약'}))
        else:
            st.warning("조건에 맞는 검색 결과가 없습니다.")
