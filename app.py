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

# 2. API 키 로드
naver_id = st.secrets.get("NAVER_CLIENT_ID", "")
naver_secret = st.secrets.get("NAVER_CLIENT_SECRET", "")

# 3. 사이드바 설정
with st.sidebar:
    st.header("⚙️ 분석 설정")
    if not naver_id:
        naver_id = st.text_input("Naver Client ID", type="password")
        naver_secret = st.text_input("Naver Client Secret", type="password")
    
    search_option = st.radio("데이터 출처", ["블로그만", "카페만", "블로그+카페 통합"])
    
    today = datetime.date.today()
    start_date = st.date_input("시작일", today - datetime.timedelta(days=30))
    end_date = st.date_input("종료일", today)
    
    total_to_collect = st.select_slider("수집 개수 (출처당)", options=[100, 300, 500, 1000], value=300)

st.title(f"🏥 경보제약 네이버 여론 분석기")

# 4. 검색창 (필수 포함 단어 추가)
col_k1, col_k2 = st.columns([3, 1])
with col_k1:
    target_keyword = st.text_input("분석 키워드 입력", value="티스템")
with col_k2:
    must_include = st.text_input("필수 포함 단어 (선택)", placeholder="예: 무릎, 연골")

if st.button("데이터 분석 시작 🚀"):
    if not naver_id or not naver_secret:
        st.error("API 키를 설정해주세요.")
    else:
        all_items = []
        api_list = ["blog"] if search_option == "블로그만" else ["cafearticle"] if search_option == "카페만" else ["blog", "cafearticle"]

        with st.spinner('데이터를 수집하고 분석하는 중...'):
            for api_type in api_list:
                for i in range(0, total_to_collect, 100):
                    start_num = i + 1
                    # URL 인코딩 처리
                    query = urllib.parse.quote(target_keyword)
                    url = f"https://openapi.naver.com/v1/search/{api_type}?query={query}&display=100&start={start_num}&sort=sim"
                    headers = {"X-Naver-Client-Id": naver_id, "X-Naver-Client-Secret": naver_secret}
                    
                    res = requests.get(url, headers=headers)
                    if res.status_code == 200:
                        items = res.json().get('items', [])
                        if not items: break
                        for item in items:
                            clean_desc = item['description'].replace('<b>','').replace('</b>','').replace('&quot;','')
                            # 필수 포함 단어 필터링
                            if must_include:
                                if must_include in item['title'] or must_include in clean_desc:
                                    item['source'] = "블로그" if api_type == "blog" else "카페"
                                    item['clean_desc'] = clean_desc
                                    all_items.append(item)
                            else:
                                item['source'] = "블로그" if api_type == "blog" else "카페"
                                item['clean_desc'] = clean_desc
                                all_items.append(item)
                    time.sleep(0.1)

        if all_items:
            df = pd.DataFrame(all_items)
            full_text = " ".join(df['clean_desc'].tolist())
            
            # 형태소 분석기 및 사용자 정의 교정
            okt = Okt()
            raw_nouns = okt.nouns(full_text)
            
            # '티스' -> '티스템'으로 교정 및 불필요한 단어 제거
            processed_nouns = []
            for n in raw_nouns:
                if n == "티스": n = "티스템" # 잘린 단어 복구
                if len(n) > 1 and n != target_keyword and n != must_include:
                    processed_nouns.append(n)
            
            counts = Counter(processed_nouns)
            
            # --- 대시보드 시각화 ---
            st.subheader("☁️ 키워드 시각화 (WordCloud)")
            f_path = get_font_path()
            if f_path and processed_nouns:
                # 색상 테마를 'viridis'로 설정하여 더 깔끔하게 변경
                wc = WordCloud(font_path=f_path, background_color='white', width=1000, height=450, 
                               max_words=100, colormap='viridis', contour_width=1).generate_from_frequencies(counts)
                fig_wc, ax_wc = plt.subplots(figsize=(12, 5))
                ax_wc.imshow(wc, interpolation='bilinear')
                ax_wc.axis('off')
                st.pyplot(fig_wc)

            st.markdown("---")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.subheader("🔝 연관어 Top 10")
                st.table(pd.DataFrame(counts.most_common(10), columns=['키워드', '빈도']))
            
            # 긍부정 분석 (생략 가능하나 유지)
            pos_dict = ['효과', '추천', '만족', '성공', '좋은', '개선', '도움']
            neg_dict = ['부작용', '비싼', '부담', '실패', '아쉬운', '통증']
            
            with c2:
                st.subheader("😊 긍정 키워드")
                pos_list = Counter([w for w in okt.morphs(full_text) if w in pos_dict]).most_common(10)
                st.table(pd.DataFrame(pos_list, columns=['단어', '빈도']))
            with c3:
                st.subheader("😟 부정 키워드")
                neg_list = Counter([w for w in okt.morphs(full_text) if w in neg_dict]).most_common(10)
                st.table(pd.DataFrame(neg_list, columns=['단어', '빈도']))

            st.markdown("---")
            csv = df[['source', 'title', 'link', 'clean_desc']].to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 데이터 다운로드 (CSV)", csv, f"{target_keyword}_분석.csv", "text/csv")
            st.dataframe(df[['source', 'title', 'link', 'clean_desc']])
        else:
            st.warning("조건에 맞는 검색 결과가 없습니다.")
