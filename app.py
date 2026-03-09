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

# 1. 페이지 설정 (요청하신 타이틀로 변경)
st.set_page_config(page_title="경보제약 네이버 여론 분석기", layout="wide")

# 한글 폰트 경로 설정
def get_font_path():
    paths = ['NanumGothic.ttf', '/usr/share/fonts/truetype/nanum/NanumGothic.ttf']
    for p in paths:
        if os.path.exists(p): return p
    return None

# 2. API 키 자동 로드
naver_id = st.secrets.get("NAVER_CLIENT_ID", "")
naver_secret = st.secrets.get("NAVER_CLIENT_SECRET", "")

# 3. 사이드바 설정 (기간 설정 및 출처 선택)
with st.sidebar:
    st.header("⚙️ 분석 설정")
    if not naver_id:
        naver_id = st.text_input("Naver Client ID", type="password")
        naver_secret = st.text_input("Naver Client Secret", type="password")
    
    # 출처 선택
    search_option = st.radio("데이터 출처 선택", ["블로그만", "카페만", "블로그+카페 통합"])
    
    # 기간 설정 (UI상 가이드 역할)
    today = datetime.date.today()
    start_date = st.date_input("시작일", today - datetime.timedelta(days=30))
    end_date = st.date_input("종료일", today)
    
    # 수집 개수
    total_to_collect = st.select_slider("수집 개수 설정 (출처당)", options=[100, 300, 500, 1000], value=300)

st.title(f"🏥 경보제약 네이버 여론 분석기")
target_keyword = st.text_input("분석 키워드 입력", value="티스템")

if st.button("데이터 분석 및 추출 시작 🚀"):
    if not naver_id or not naver_secret:
        st.error("API 키를 설정해주세요.")
    else:
        all_items = []
        api_list = []
        if search_option == "블로그만": api_list = ["blog"]
        elif search_option == "카페만": api_list = ["cafearticle"]
        else: api_list = ["blog", "cafearticle"]

        progress_bar = st.progress(0)
        total_steps = len(api_list) * (total_to_collect // 100)
        current_step = 0

        with st.spinner('데이터를 수집하고 분석하는 중...'):
            for api_type in api_list:
                for i in range(0, total_to_collect, 100):
                    start_num = i + 1
                    encoded_keyword = urllib.parse.quote(target_keyword)
                    url = f"https://openapi.naver.com/v1/search/{api_type}?query={encoded_keyword}&display=100&start={start_num}&sort=sim"
                    headers = {"X-Naver-Client-Id": naver_id, "X-Naver-Client-Secret": naver_secret}
                    
                    res = requests.get(url, headers=headers)
                    if res.status_code == 200:
                        items = res.json().get('items', [])
                        if not items: break
                        for item in items:
                            item['source'] = "블로그" if api_type == "blog" else "카페"
                        all_items.extend(items)
                    
                    time.sleep(0.1)
                    current_step += 1
                    progress_bar.progress(min(current_step / total_steps, 1.0))

        if all_items:
            df = pd.DataFrame(all_items)
            df['내용'] = df['description'].str.replace('<b>','').str.replace('</b>','').str.replace('&quot;','')
            full_text = " ".join(df['내용'].tolist())
            
            # 형태소 분석
            okt = Okt()
            nouns = [n for n in okt.nouns(full_text) if len(n) > 1 and n != target_keyword]
            
            # 데이터 집계
            top_nouns = Counter(nouns).most_common(10)
            pos_dict = ['효과', '추천', '만족', '성공', '좋은', '개선', '도움', '혁신', '최고', '정상']
            neg_dict = ['부작용', '비싼', '부담', '실패', '아쉬운', '통증', '주의', '논란', '힘든', '걱정']
            
            words = okt.morphs(full_text)
            top_pos = Counter([w for w in words if w in pos_dict]).most_common(10)
            top_neg = Counter([w for w in words if w in neg_dict]).most_common(10)

            # --- 대시보드 시각화 ---
            # 1. 워드클라우드 (상단 배치)
            st.subheader("☁️ 주요 키워드 시각화 (WordCloud)")
            f_path = get_font_path()
            if f_path and nouns:
                wc = WordCloud(font_path=f_path, background_color='white', width=1000, height=400).generate_from_frequencies(Counter(nouns))
                fig_wc, ax_wc = plt.subplots(figsize=(10, 4))
                ax_wc.imshow(wc, interpolation='bilinear')
                ax_wc.axis('off')
                st.pyplot(fig_wc)
            else:
                st.info("폰트 파일이 없거나 분석할 키워드가 부족하여 워드클라우드를 표시할 수 없습니다.")

            st.markdown("---")

            # 2. 순위 표 (중단 배치)
            c1, c2, c3 = st.columns(3)
            with c1:
                st.subheader("🔝 연관어 Top 10")
                st.table(pd.DataFrame(top_nouns, columns=['키워드', '빈도']))
            with c2:
                st.subheader("😊 긍정어 순위")
                st.table(pd.DataFrame(top_pos, columns=['단어', '빈도']))
            with c3:
                st.subheader("😟 부정어 순위")
                st.table(pd.DataFrame(top_neg, columns=['단어', '빈도']))

            # 3. 데이터 다운로드 및 원문 (하단 배치)
            st.markdown("---")
            csv = df[['source', 'title', 'link', '내용']].to_csv(index=False).encode('utf-8-sig')
            st.download_button(label="📥 분석 데이터 전체 다운로드 (Excel/CSV)", data=csv, file_name=f"{target_keyword}_경보제약_분석.csv", mime='text/csv')
            
            st.subheader(f"📋 수집 원문 (총 {len(all_items)}건 / {start_date} ~ {end_date})")
            st.dataframe(df[['source', 'title', 'link', '내용']].rename(columns={'source': '출처'}))
        else:
            st.warning("수집된 데이터가 없습니다.")
