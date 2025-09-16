# --------------------------------------------------------------------------
#                           라이브러리 불러오기
# --------------------------------------------------------------------------
import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import os

# PDF 라이브러리 조건부 import
try:
    from fpdf2 import FPDF
    PDF_AVAILABLE = True
except ImportError:
    try:
        from fpdf import FPDF
        PDF_AVAILABLE = True
    except ImportError:
        PDF_AVAILABLE = False

# --------------------------------------------------------------------------
#                           1. 기본 페이지 설정 및 데이터 로딩
# --------------------------------------------------------------------------

st.set_page_config(page_title="상급종합병원 비급여 항목 분석", layout="wide")
st.title("상급종합병원 비급여 항목 분석")

@st.cache_data
def load_data():
    try:
        df = pd.read_parquet("data.parquet")
        if 'npay_code' in df.columns:
            df['npay_code'] = df['npay_code'].astype(str)
        return df
    except FileNotFoundError:
        st.error("오류: 'data.parquet' 파일을 찾을 수 없습니다. app.py와 같은 폴더에 데이터 파일을 넣어주세요.")
        st.stop()

df = load_data()

# --------------------------------------------------------------------------
#                           2. PDF 리포트 생성 함수
# --------------------------------------------------------------------------
def create_pdf_report(item_name, stats, median_price, hospital_data):
    if not PDF_AVAILABLE:
        st.error("PDF 라이브러리가 설치되지 않았습니다.")
        return None
        
    pdf = FPDF()
    pdf.add_page()
    
    # 폰트 설정 함수
    def set_font_safe(size):
        try:
            font_path = os.path.join(os.path.dirname(__file__), 'NanumGothic.ttf')
            if os.path.exists(font_path):
                pdf.add_font('NanumGothic', '', font_path, uni=True)
                pdf.set_font('NanumGothic', '', size)
            else:
                pdf.set_font('Arial', '', size)
        except:
            pdf.set_font('Arial', '', size)
    
    set_font_safe(16)
    
    # 리포트 제목
    pdf.cell(0, 10, "Non-covered Medical Items Analysis Report", ln=True, align='C')
    pdf.ln(10)
    
    # 분석 항목명
    set_font_safe(12)
    pdf.cell(0, 10, f"Item: {item_name}", ln=True)
    pdf.ln(5)

    # 가격 통계
    pdf.cell(0, 10, "Price Statistics", ln=True)
    set_font_safe(10)
    pdf.multi_cell(0, 8,
        f"Average: {int(stats['mean']):,} KRW\n"
        f"Median: {int(median_price):,} KRW\n"
        f"Min: {int(stats['min']):,} KRW\n"
        f"Max: {int(stats['max']):,} KRW\n"
        f"Hospitals: {int(stats['count'])}"
    )
    pdf.ln(5)
    
    # 병원별 가격 목록
    set_font_safe(12)
    pdf.cell(0, 10, "Hospital Price List", ln=True)
    set_font_safe(10)
    
    # 테이블 헤더
    pdf.cell(130, 8, 'Hospital', 1, 0, 'C')
    pdf.cell(60, 8, 'Price (KRW)', 1, 1, 'C')
    
    # 테이블 내용
    for index, row in hospital_data.iterrows():
        hospital_name = str(row['hospital_name'])[:30]
        pdf.cell(130, 8, hospital_name, 1)
        pdf.cell(60, 8, f"{int(row['price']):,}", 1, 1, 'R')
        
    # PDF 내용을 바이너리로 반환
    return bytes(pdf.output())

# --------------------------------------------------------------------------
#                           3. 사이드바 UI 구성
# --------------------------------------------------------------------------
st.sidebar.header("검색")
search_options = ['항목명', '병원명', '항목 코드']
selected_scopes = st.sidebar.multiselect("검색할 범위를 선택하세요", options=search_options, default=['항목명'])
search_keyword = st.sidebar.text_input("검색어를 입력하세요", placeholder="선택된 범위 내에서 검색합니다")

st.sidebar.divider()
st.sidebar.header("상세 분석")
item_search_keyword = st.sidebar.text_input("분석할 항목 검색", placeholder="분석하고 싶은 항목을 검색하세요")

if item_search_keyword:
    filtered_item_list = sorted([item for item in df['item_name'].unique() if item_search_keyword.lower() in item.lower()])
else:
    filtered_item_list = []
selected_item = st.sidebar.selectbox("항목 선택 (위에서 먼저 검색)", options=filtered_item_list, index=None, placeholder="항목을 선택하세요")


# --------------------------------------------------------------------------
#                           4. 메인 화면 구성
# --------------------------------------------------------------------------
st.header("데이터 조회 결과")

# 고급 검색 로직
if search_keyword and selected_scopes:
    conditions = []
    if '항목명' in selected_scopes: conditions.append(df['item_name'].str.contains(search_keyword, case=False, na=False))
    if '병원명' in selected_scopes: conditions.append(df['hospital_name'].str.contains(search_keyword, case=False, na=False))
    if '항목 코드' in selected_scopes and 'npay_code' in df.columns: conditions.append(df['npay_code'].str.contains(search_keyword, case=False, na=False))
    if conditions:
        final_condition = np.logical_or.reduce(conditions)
        df_filtered = df[final_condition]
    else: df_filtered = df
elif not selected_scopes and search_keyword:
    st.warning("검색할 범위를 1개 이상 선택해주세요.")
    df_filtered = pd.DataFrame()
else: df_filtered = df
st.dataframe(df_filtered)
st.info(f"조회된 항목 수: **{len(df_filtered)}** 건")


# 상세 분석 정보 표시
if selected_item:
    st.divider()
    st.header(f"'{selected_item}' 상세 분석")
    df_selected = df[df['item_name'] == selected_item]
    stats = df_selected['price'].describe()
    median_price = df_selected['price'].median()
    
    st.subheader("통계 요약")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("평균 가격", f"{int(stats['mean']):,} 원")
    col2.metric("중앙값", f"{int(median_price):,} 원")
    col3.metric("최저가", f"{int(stats['min']):,} 원")
    col4.metric("최고가", f"{int(stats['max']):,} 원")
    col5.metric("취급 병원 수", f"{int(stats['count'])} 곳")
    
    st.subheader("병원별 가격 분포")
    fig = px.box(df_selected, x='hospital_name', y='price', title=f"'{selected_item}' 병원별 가격 분포", labels={'hospital_name': '병원명', 'price': '가격 (원)'})
    fig.update_xaxes(tickangle=45)
    st.plotly_chart(fig, use_container_width=True)

    # --- 리포트 및 PDF 다운로드 기능 ---
    st.divider()
    st.header("분석 리포트")

    # 화면에 병원별 가격 리스트 표시
    st.subheader("병원별 가격 목록")
    report_df = df_selected[['hospital_name', 'price']].sort_values(by='price', ascending=False).reset_index(drop=True)
    st.dataframe(report_df)

    # PDF 생성
    if PDF_AVAILABLE:
        try:
            pdf_data = create_pdf_report(selected_item, stats, median_price, report_df)
            
            if pdf_data:
                # PDF 다운로드 버튼
                st.download_button(
                    label="리포트 PDF로 다운로드",
                    data=pdf_data,
                    file_name=f"{selected_item}_report.pdf",
                    mime="application/pdf"
                )
        except Exception as e:
            st.error(f"PDF 생성 중 오류가 발생했습니다: {e}")
    else:
        st.info("PDF 다운로드 기능을 사용하려면 fpdf2 라이브러리를 설치하세요.")
