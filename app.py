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
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
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

tab1, tab2 = st.tabs(["📸 카메라로 촬영", "📁 파일 업로드"])

with tab1:
    cam_file = st.camera_input("제품의 라벨이 잘 보이도록 촬영해 주세요.")
    with st.expander("❓ 카메라 화면이 안 나오거나 먹통인가요? (해결 방법)"):
        st.markdown("""\n 1. 카카오톡은 카메라 기능을 지원하지않습니다. 크롬등의 브라우저에서 접속해주세요.\n
        2. 크롬등의 브라우저에서는 카메라 허용설정을 해야합니다. 우측상단 점세개->설정->사이트설정->카메라->요청할수있음 으로 설정하고 새로고침하면됩니다.\n
        3. 브라우저 자체(크롬등)의 카메라 허용권한을 기기내에서 허용해주셔야 카메라 촬영이 가능합니다.""")

with tab2:
    img_file = st.file_uploader("확인하고자 하는 제품의 사진을 업로드 해주세요.", type=['png', 'jpg', 'jpeg'])

uploaded_file = cam_file if cam_file is not None else img_file

# 인식 로직 
if uploaded_file and db_df is not None:
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.image(uploaded_file, caption="분석 대상 사진", use_container_width=True)
        
    with col2:
        file_identifier = uploaded_file.name if hasattr(uploaded_file, 'name') else "camera_image"
        
        if "ai_name" not in st.session_state or st.session_state.get("last_uploaded_img") != file_identifier:
            with st.spinner("분석 중..."):
                img = Image.open(uploaded_file)
                prompt = "사진 속 제품 라벨에 가장 크게 적힌 한국어 제품명만 딱 한 줄로 말해줘 띄어쓰기없이.  (예: 토레타, 카스타드), 단 영어가 가장 크게적힌 단어일경우, 영단어를 한글로 해석하여 표기해. (예: Lipton ->립톤)"
                response = model.generate_content([prompt, img])
                st.session_state.ai_name = response.text.strip().replace("!", "")
                st.session_state.last_uploaded_img = file_identifier

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
        # 1. 식약처 기준 일일 영양성분 기준치 데이터 (성인 기준)
        daily_standards = {
            'calories': 2000,      # 열량: 2000kcal
            'natrium': 2000,       # 나트륨: 2000mg
            'carbs': 324,          # 탄수화물: 324g
            'sugar': 100,          # 당류: 100g
            'fat': 54,             # 지방: 54g
            't_fat': 2,            # 트랜스지방산: 약 2g 제한
            'p_fat': 15,           # 포화지방산: 15g
            'chole': 300,          # 콜레스테롤: 300mg
            '단백질': 55           # 단백질: 55g (식약처 데이터 매핑명 확인 필요)
        }
        
        # 2. 일일 기준치 대비 비율(%) 계산 및 최대 섭취 가능 개수 산출
        st.markdown("---")
        st.subheader("⚠️ 영양성분 과다섭취 경고 패널")
        
        # 가장 위험한 요소(비율이 가장 높은 요소)를 찾기 위한 변수들
        max_percentage = 0
        danger_nutrient = ""
        limit_count = 99
        
        # 체크할 영양소 리스트 (식약처 기준치 매핑명과 맞춰야 합니다)
        check_nutrients = [
            ('열량', res['calories'], daily_standards['calories'], 'kcal'),
            ('나트륨', res['natrium'], daily_standards['natrium'], 'mg'),
            ('탄수화물', res['carbs'], daily_standards['carbs'], 'g'),
            ('당류', res['sugar'], daily_standards['sugar'], 'g'),
            ('지방', res['fat'], daily_standards['fat'], 'g'),
            ('포화지방산', res['p_fat'], daily_standards['p_fat'], 'g'),
            ('콜레스테롤', res['chole'], daily_standards['chole'], 'mg'),
        ]
        
        # 화면 레이아웃 (퍼센트 수치 나열)
        col_pct1, col_pct2 = st.columns(2)
        
        with col_pct1:
            st.markdown("**📊 이 제품 1개 섭취 시 일일 기준치 비율**")
            for name, value, std, unit in check_nutrients:
                if value > 0:
                    pct = (value / std) * 100
                    st.write(f"• {name}: **{pct:.1f}%** ({value}{unit} / {std}{unit})")
                    
                    # 1개만 먹어도 하루 기준치를 가장 많이 채우는 성분 추적
                    if pct > max_percentage:
                        max_percentage = pct
                        danger_nutrient = name
                        # 해당 성분 기준으로 하루에 몇 개까지 먹을 수 있는지 계산 (소수점 버림)
                        limit_count = int(std // value) if value > 0 else 99
        
        with col_pct2:
            # 3. 경각심을 주는 큰 폰트 경고 창 (HTML/CSS 사용)
            st.markdown("**🚨 연속 섭취 제한 경고**")
            if danger_nutrient != "" and limit_count < 99:
                # 안전/경고 수치에 따른 색상 분기
                box_color = "#FF4B4B" if limit_count <= 2 else "#FFA500" # 2개 이하면 빨강, 아니면 주황
                
                if limit_count == 0:
                    alert_text = f"🚨 이 제품은 1개만 먹어도 하루 <b>{danger_nutrient}</b> 기준치를 초과합니다!"
                else:
                    alert_text = f"⚠️ 하루에 최대 <span style='font-size:32px; font-weight:bold;'>{limit_count}개</span>까지만 드세요!"
                    
                st.markdown(f"""
                    <div style="background-color: {box_color}22; border: 2px solid {box_color}; padding: 20px; border-radius: 10px; text-align: center;">
                        <p style="font-size: 18px; margin-bottom: 5px; color: white;">가장 높은 비율 성분: <b>{danger_nutrient} ({max_percentage:.1f}%)</b></p>
                        <h2 style="color: {box_color}; margin-top: 0px; font-size: 28px;">{alert_text}</h2>
                        <p style="font-size: 13px; color: #aaa; margin-top: 10px;">* 식약처 성인 하루 영양성분 기준치 데이터 기반</p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("영양성분 데이터가 부족하여 경고를 계산할 수 없습니다.")
        

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
                st.markdown("##### 📈 7일간 누적 트래픽 추이")
                st.bar_chart(df_weekly, color="#FF4B4B")
                
            with tab_monthly:
                st.markdown("##### 📉 12개월 누적 트래픽 추이")
                st.line_chart(df_monthly, color="#29B5E8")
                
            st.divider()

        except FileNotFoundError:
            st.warning("🔄 데이터 수집 중입니다.")

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
        st.write("개발버전: v1.04(카메라기능 추가)")
        st.write("최종개발수정일: 12/06/2026")

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
