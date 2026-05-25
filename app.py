import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import matplotlib.pyplot as plt
import os
from datetime import datetime

#페이지 트래픽 계산용 함수
def record_traffic():
    file_path = "traffic_log.csv"
    if not os.path.exists(file_path):
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("timestamp\n")
            
    with open(file_path, "a", encoding="utf-8") as f:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"{now}\n")

# 페이지 새로 고침수마다 트래픽 1증가
record_traffic()

# API 설정
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]   
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-flash-latest')

# 식약처 데이터베이스 로드 함수
@st.cache_data
def load_db():
    try:
        df = pd.read_csv('food_db.csv', encoding='utf-8')
        return df
    except FileNotFoundError:
        st.error("food_db.csv 파일을 찾을 수 없습니다!")
        return None

# 모바일의 한국어를 다시 번역하는 이상한 자동번역방지용 코드 
st.set_page_config(page_title="데이터베이스 및 이미지인식기술 기반  영양성분인식 프로그램", layout="wide")
st.markdown("""
    <head>
        <meta name="google" content="notranslate">
    </head>
    <style>
        * {
            translate: no !important;
        }
        .stMarkdown, .stTable, [data-testid="stMetricValue"] {
            unicode-bidi: isolate;
        }
    </style>
    <script>
        document.documentElement.classList.add('notranslate');
        document.querySelector('meta[name="google"]').setAttribute('content', 'notranslate');
    </script>
""", unsafe_allow_html=True)
#상단 정보표시란
st.title("영양성분 인식프로그램 ")

#핵심로직
db_df = load_db()
img_file = st.file_uploader("확인하고자 하는 제품의 사진을 업로드 해주세요.", type=['png', 'jpg', 'jpeg'])
#인식로직
if img_file and db_df is not None:
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.image(img_file, caption="분석 대상 사진", use_container_width=True)
        
    with col2:
        if "ai_name" not in st.session_state or st.session_state.get("last_uploaded_img") != img_file.name:
            with st.spinner("분석 중..."):
                img = Image.open(img_file)
                prompt = "사진 속 제품 라벨에 가장 크게 적힌 한국어 제품명만 딱 한 줄로 말해줘 띄어쓰기없이.  (예: 토레타, 카스타드), 단 영어가 가장 크게적힌 단어일경우, 영단어를 한글로 해석하여 표기해. (예: Lipton ->립톤) "
                response = model.generate_content([prompt, img])
                st.session_state.ai_name = response.text.strip().replace("!", "")
                st.session_state.last_uploaded_img = img_file.name

        ai_name = st.session_state.ai_name
        
        search_results = db_df[db_df['식품명'].str.contains(ai_name, na=False)].copy()
        #결과로직     
        if not search_results.empty:
            st.success(f"✅ 인식 단어: **{ai_name}**")
            
            search_results['display_label'] = (
                search_results['식품명'] + " [" + 
                search_results['에너지(kcal)'].astype(str) + "kcal / " + 
                search_results['식품중량'].astype(str) + "]"
            )
            display_list = search_results['display_label'].drop_duplicates().tolist()
            
            selected_item = st.selectbox(
                f"'{ai_name}' 검색 결과입니다. 용량과 칼로리를 확인하여 찿고자 하는 제품명을 선택하세요. **제품명을 여러번 다시 선택할경우 갱신이 안될수있으니 여러번 선택하신경우 사진을 다시 올리시는것을 추천드립니다.**:",
                display_list,
                key="product_select_box"
            )

            with st.container(key=f"result_{selected_item}"):
                selected_row = search_results[search_results['display_label'] == selected_item].iloc[0]

                res = {
                    "name": selected_row['식품명'],
                    "calories": selected_row['에너지(kcal)'],
                    "natrium": selected_row['나트륨(mg)'],
                    "sugar": selected_row['당류(g)'],
                    "protein": selected_row['단백질(g)'],
                    "fat": selected_row['지방(g)'],
                    "carbs": selected_row['탄수화물(g)'],
                    "p_fat": selected_row['포화지방산(g)'],
                    "t_fat": selected_row['트랜스지방산(g)'],
                    "chole": selected_row['콜레스테롤(mg)']
                }
                #정보표시용 데이터

                st.divider()
                st.subheader(f"📌 {res['name']} 핵심 지표")
                
                m1, m2, m3 = st.columns(3)
                m1.metric("🔥 열 량", f"{res['calories']} kcal")
                m2.metric("🍭 당 류", f"{res['sugar']} g")
                m3.metric("🧂 나 트 륨 ", f"{res['natrium']} mg")
                st.subheader("📊 영양성분 리포트")
                
                # 그래프용 데이터 
                nutrition_labels = ["열량", "나트륨", "탄수화물", "당류", "지방", "트랜스지방산", "포화지방산", "콜레스테롤", "단백질"]
                nutrition_values = [res['calories'], res['natrium'], res['carbs'], res['sugar'], res['fat'], res['t_fat'], res['p_fat'], res['chole'], res['protein']]

                # 한글 폰트
                plt.rcParams['font.family'] = 'NanumGothic' 
                plt.rcParams['axes.unicode_minus'] = False

                fig, ax = plt.subplots(figsize=(10, 5))
                bars = ax.bar(nutrition_labels, nutrition_values, color='skyblue')

                for bar in bars:
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                            f'{height}', ha='center', va='bottom', fontsize=9)
                # 하단 영양성분 표시용 데이터

                ax.set_ylabel('함량')
                ax.grid(axis='y', linestyle='--', alpha=0.7)

                st.pyplot(fig)
                
                with st.expander("📝 각 성분별 정확한 수치 확인"):
                    table_df = pd.DataFrame({
                        "영양성분": ["열량(kcal)", "나트륨(mg)", "탄수화물(g)", "당류(g)", "지방(g)", "트랜스지방(g)", "포화지방(g)", "콜레스테롤(mg)", "단백질(g)"],
                        "함량": nutrition_values
                    })
                    st.table(table_df)           
        else:
            st.warning(f"인식된 단어 '{ai_name}'에 해당하는 제품을 DB에서 찾을 수 없습니다.")

#심포지엄 활동용으로 추가한 트래픽 분석기능 (개발자전용)

st.divider()

with st.expander("🔐 [관리자 전용] 트래픽 관제 패널"):
    
    # 1. 관리자 패스워드 검증
    admin_password = st.text_input("관리자용 비밀번호를 입력하세요.", type="password", key="admin_pwd")
    
    if admin_password == "admin1234":
        st.success("🔒 인증 성공")
        st.divider()
        
        # 2. traffic_log.csv 파일 읽기 및 Pandas 연산
        try:
            # 실제 로그 파일 불러오기
            df_traffic = pd.read_csv("traffic_log.csv")
            df_traffic['timestamp'] = pd.to_datetime(df_traffic['timestamp'])
            
            # (1) 일간  통계
            df_traffic['hour'] = df_traffic['timestamp'].dt.hour
            hourly_counts = df_traffic['hour'].value_counts().reindex(range(24), fill_value=0)
            hours_labels = [f"{i:02d}시" for i in range(24)]
            df_daily = pd.DataFrame({"접속량 (API 호출 수)": hourly_counts.values}, index=hours_labels)

            # (2) 주간 통계
            df_traffic['weekday'] = df_traffic['timestamp'].dt.weekday
            weekday_counts = df_traffic['weekday'].value_counts().reindex(range(7), fill_value=0)
            days_labels = ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']
            df_weekly = pd.DataFrame({"접속량 (API 호출 수)": weekday_counts.values}, index=days_labels)

            # (3) 월간 통계
            df_traffic['month'] = df_traffic['timestamp'].dt.month
            month_counts = df_traffic['month'].value_counts().reindex(range(1, 13), fill_value=0)
            months_labels = [f"{i}월" for i in range(1, 13)]
            df_monthly = pd.DataFrame({"누적 접속자 수": month_counts.values}, index=months_labels)

            # 3. 트래픽 시각화 탭 구성
            st.subheader("📊 웹사이트 트래픽 용량 지표")
            tab_daily, tab_weekly, tab_monthly = st.tabs(["📅 일간 트래픽", "📆 주간 트래픽", "🗓️ 월간 트래픽"])
            
            with tab_daily:
                st.markdown("##### 🕒 24시간 실시간 트래픽 추이")
                st.area_chart(df_daily, color="#0068C9")
                
            with tab_weekly:
                st.markdown("##### 📈 7일간 누적 트래픽 변동 추이")
                st.bar_chart(df_weekly, color="#FF4B4B")
                
            with tab_monthly:
                st.markdown("##### 📉 12개월 누적 접속자 수 트렌드")
                st.line_chart(df_monthly, color="#29B5E8")
                
            st.divider()

        except FileNotFoundError:
            st.warning("🔄 데이터 수집 중입니다. (아직 누적된 트래픽 로그 파일이 없거나 생성 중입니다.)")

    elif admin_password != "":
        st.error("❌ 인증 실패: 패스워드가 일치하지 않습니다.")

#하단 정보표시란 
st.divider() 


footer_container = st.container()

with footer_container:
    col_info, col_team = st.columns([3, 1])
    
    with col_info:
        st.markdown("#### 📊 데이터 출처 및 정보")
        st.write("**사용한 데이터베이스:** 식품영양성분 데이터베이스")
        st.write("**English:** Korean Food Composition Database system(K-FCDB)")
        st.caption("본 서비스는 식품의약품 안전처의 DB를 기반으로 제작되었습니다.")

    with col_team:
        st.markdown("#### 식품영양성분 분석 프로그램 ")
        st.write("초당고등학교 프로젝트봉사활동")
        st.write("오류 및 문의사항 : 010-8671-0179(문자메시지 또는 카카오톡)")
        st.write("개발버전: v1.02")
        st.write("최종개발수정일: 06/05/2026")

st.markdown(
    """
    <style>
    .footer-text {
        text-align: center;
        color: grey;
        font-size: 0.8em;
        margin-top: 50px;
    }
    </style>
    <div class="footer-text">
        © 2026 chodang ocr1. All rights reserved.
    </div>
    """,
    unsafe_allow_html=True
)
