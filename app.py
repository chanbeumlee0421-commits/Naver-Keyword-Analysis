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
import numpy as np

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

# 4. 검색 필터부
col_k1, col_k2, col_k3 = st.columns([2, 1, 1])
with col_k1:
    target_keyword = st.text_input("분석 키워드 입력", value="티스템")
with col_k2:
    must_include = st.text_input("필수 포함 단어", placeholder="예: 무릎")
with col_k3:
    exclude_words = st.text_input("제외할 단어 (쉼표 구분)", placeholder="예: 광고, 포스팅")

if st.button("데이터 분석 시작 🚀"):
    if not naver_id or not naver_secret:
        st.error("API 키를 설정해주세요.")
    else:
        all_items = []
        api_list = ["blog"] if search_option == "블로그만" else ["cafearticle"] if search_option == "카페만" else ["blog", "cafearticle"]
        stop_words = [x.strip() for x in exclude_words.split(',')] if exclude_words else []

        with st.spinner('데이터 수집 중...'):
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
                            if must_include and (must_include not in item['title'] and must_include not in clean_desc):
                                continue
                            item['source'] = "블로그" if api_type == "blog" else "카페"
                            item['clean_desc'] = clean_desc
                            all_items.append(item)
                    time.sleep(0.1)

        if all_items:
            df = pd.DataFrame(all_items)
            
            # --- 상단 통계 지표 ---
            st.markdown("---")
            m1, m2, m3 = st.columns(3)
            blog_cnt = len(df[df['source'] == '블로그'])
            cafe_cnt = len(df[df['source'] == '카페'])
            m1.metric("전체 수집 게시글", f"{len(df)} 건")
            m2.metric("블로그 게시글", f"{blog_cnt} 건")
            m3.metric("카페 게시글", f"{cafe_cnt} 건")

            # 형태소 분석
            full_text = " ".join(df['clean_desc'].tolist())
            okt = Okt()
            raw_nouns = okt.nouns(full_text)
            
            # [근본 해결] 검색어 파편화 자동 복구 로직
            # 검색어가 '티스템'이면 '티스'를 찾아 '티스템'으로 자동 치환
            prefix_target = target_keyword[:2] # 검색어 앞 두 글자 추출
            
            processed_nouns = []
            for n in raw_nouns:
                if n == prefix_target and len(target_keyword) > 2:
                    n = target_keyword
                
                if len(n) > 1 and n != target_keyword and n not in stop_words:
                    processed_nouns.append(n)
            
            counts = Counter(processed_nouns)
            
            # --- 시각화 레이아웃 ---
            col_left, col_right = st.columns([1.5, 1])
            
            with col_left:
                st.subheader("☁️ 키워드 시각화")
                f_path = get_font_path()
                if f_path and processed_nouns:
                    # 원형 마스크 생성 (디자인 개선)
                    x, y = np.ogrid[:600, :600]
                    mask = (x - 300) ** 2 + (y - 300) ** 2 > 260 ** 2
                    mask = 255 * mask.astype(int)

                    wc = WordCloud(
                        font_path=f_path, 
                        background_color='white', 
                        mask=mask,
                        width=600, height=600, 
                        max_words=100, 
                        colormap='tab10', # 더 선명한 색상 조합
                        prefer_horizontal=0.8,
                        contour_width=2,
                        contour_color='steelblue'
                    ).generate_from_frequencies(counts)
                    
                    fig_wc, ax_wc = plt.subplots(figsize=(8, 8))
                    ax_wc.imshow(wc, interpolation='bilinear')
                    ax_wc.axis('off')
                    st.pyplot(fig_wc)
            
            with col_right:
                st.subheader("🔝 연관 키워드 TOP 15")
                st.table(pd.DataFrame(counts.most_common(15), columns=['단어', '빈도']))

            st.markdown("---")
            c1, c2 = st.columns(2)
            pos_dict = ['효과', '추천', '만족', '성공', '좋은', '개선', '도움', '강추', '완화']
            neg_dict = ['부작용', '비싼', '부담', '실패', '아쉬운', '통증', '재발', '걱정']
            
            with c1:
                st.subheader("😊 긍정 반응 분석")
                pos_list = Counter([w for w in okt.morphs(full_text) if w in pos_dict]).most_common(10)
                st.table(pd.DataFrame(pos_list, columns=['긍정어', '빈도']))
            with c2:
                st.subheader("😟 부정 반응 분석")
                neg_list = Counter([w for w in okt.morphs(full_text) if w in neg_dict]).most_common(10)
                st.table(pd.DataFrame(neg_list, columns=['부정어', '빈도']))

            st.markdown("---")
            csv = df[['source', 'title', 'link', 'clean_desc']].to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 수집 데이터 CSV 다운로드", csv, f"{target_keyword}_raw_data.csv", "text/csv")
            st.dataframe(df[['source', 'title', 'link', 'clean_desc']].rename(columns={'source':'출처', 'clean_desc':'내용'}))
        else:
            st.warning("조건에 맞는 결과가 없습니다.")
