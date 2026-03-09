import streamlit as st
import requests
import pandas as pd
from konlpy.tag import Okt
from collections import Counter
import urllib.parse
import os
import time

# 1. 페이지 및 폰트 설정
st.set_page_config(page_title="네이버 키워드 대량 분석기", layout="wide")

def get_font_path():
    paths = ['NanumGothic.ttf', '/usr/share/fonts/truetype/nanum/NanumGothic.ttf']
    for p in paths:
        if os.path.exists(p): return p
    return None

# 2. API 키 자동 로드
naver_id = st.secrets.get("NAVER_CLIENT_ID", "")
naver_secret = st.secrets.get("NAVER_CLIENT_SECRET", "")

# 3. 사이드바 - 대량 수집 설정
with st.sidebar:
    st.header("⚙️ 대량 분석 설정")
    if not naver_id:
        naver_id = st.text_input("Naver Client ID", type="password")
        naver_secret = st.text_input("Naver Client Secret", type="password")
    
    source = st.selectbox("데이터 출처", ["blog", "cafearticle"], format_func=lambda x: "네이버 블로그" if x=="blog" else "네이버 카페")
    # 네이버 API는 시작 위치(start) 최대 1000까지 지원
    total_to_collect = st.select_slider("총 수집 개수 설정", options=[100, 300, 500, 1000], value=300)
    st.caption("※ 100개 단위로 반복 호출하여 수집합니다.")

st.title(f"🚀 네이버 키워드 대량 분석 & 엑셀 추출")
target_keyword = st.text_input("분석 키워드 입력", value="티스템")

if st.button("데이터 분석 및 추출 시작"):
    if not naver_id or not naver_secret:
        st.error("API 키가 없습니다.")
    else:
        all_items = []
        progress_bar = st.progress(0)
        
        with st.spinner(f'네이버에서 {total_to_collect}개의 데이터를 긁어오는 중...'):
            # 페이징 루프 (100개씩 수집)
            for i in range(0, total_to_collect, 100):
                start_num = i + 1
                encoded_keyword = urllib.parse.quote(target_keyword)
                url = f"https://openapi.naver.com/v1/search/{source}?query={encoded_keyword}&display=100&start={start_num}&sort=sim"
                headers = {"X-Naver-Client-Id": naver_id, "X-Naver-Client-Secret": naver_secret}
                
                res = requests.get(url, headers=headers)
                if res.status_code == 200:
                    items = res.json().get('items', [])
                    if not items: break
                    all_items.extend(items)
                else:
                    st.error(f"오류 발생: {res.status_code}")
                    break
                
                # API 부하 방지를 위한 아주 짧은 휴식
                time.sleep(0.1)
                progress_bar.progress(min((i + 100) / total_to_collect, 1.0))

        if all_items:
            df = pd.DataFrame(all_items)
            df['내용'] = df['description'].str.replace('<b>','').str.replace('</b>','').str.replace('&quot;','')
            full_text = " ".join(df['내용'].tolist())
            
            # NLP 분석
            okt = Okt()
            nouns = [n for n in okt.nouns(full_text) if len(n) > 1 and n != target_keyword]
            
            # 연관어 / 긍부정 Top 10
            top_nouns = Counter(nouns).most_common(10)
            pos_dict = ['효과', '추천', '만족', '성공', '좋은', '개선', '도움', '혁신', '최고', '정상']
            neg_dict = ['부작용', '비싼', '부담', '실패', '아쉬운', '통증', '주의', '논란', '힘든', '걱정']
            
            words = okt.morphs(full_text)
            top_pos = Counter([w for w in words if w in pos_dict]).most_common(10)
            top_neg = Counter([w for w in words if w in neg_dict]).most_common(10)

            # --- 시각화 화면 ---
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

            # 엑셀 다운로드 기능 추가
            st.markdown("---")
            csv = df[['title', 'link', '내용']].to_csv(index=False).encode('utf-8-sig')
            st.download_button(label="📥 분석 결과 엑셀(CSV) 다운로드", data=csv, file_name=f"{target_keyword}_분석결과.csv", mime='text/csv')
            
            st.subheader(f"📋 수집된 원문 데이터 (총 {len(all_items)}건)")
            st.dataframe(df[['title', 'link', '내용']])
        else:
            st.warning("수집된 데이터가 없습니다.")
