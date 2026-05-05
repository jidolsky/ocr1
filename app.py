import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import matplotlib.pyplot as plt

# API 설정
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]   
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-flash-latest')

# 식약처 데이터베이스 로드 함수
@st.cache_data
def load_db():
    try:
        df = pd.read_csv('food_db.csv', encoding='cp949')
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
                prompt = "사진 속 제품 라벨에 가장 크게 적힌 한국어 제품명만 딱 한 줄로 말해줘. (예: 토레타, 카스타드)"
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
                st.subheader("📊 9대 필수 영양성분 리포트")
                
                # 그래프용 데이터 
                nutrition_labels = ["열량", "나트륨", "탄수화물", "당류", "지방", "트랜스지방산", "포화지방산", "콜레스테롤", "단백질"]
                nutrition_values = [res['calories'], res['natrium'], res['carbs'], res['sugar'], res['fat'], res['t_fat'], res['p_fat'], res['chole'], res['protein']]

                # 한글 폰트
                plt.rcParams['font.family'] = 'Malgun Gothic' 
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
        st.write("오류 및 다른사항 문의: 010-8671-0179(문자메시지 또는 카카오톡)")
        st.write("개발버전: v1.0")
        st.write("최종개발수정일: 05/05/2026")

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
