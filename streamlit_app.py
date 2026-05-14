import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Amazon Transportation Survey Dashboard",
    layout="wide"
)

# -----------------------------
# Custom Styling
# -----------------------------
st.markdown("""
<style>
.main {
    background-color: #f7f9fc;
}
.block-container {
    padding-top: 2rem;
}
.metric-card {
    background-color: white;
    padding: 20px;
    border-radius: 14px;
    box-shadow: 0px 2px 8px rgba(0,0,0,0.08);
    text-align: center;
}
.metric-title {
    font-size: 15px;
    color: #666;
}
.metric-value {
    font-size: 32px;
    font-weight: 700;
    color: #1f4e79;
}
.section-card {
    background-color: white;
    padding: 22px;
    border-radius: 14px;
    box-shadow: 0px 2px 8px rgba(0,0,0,0.06);
    margin-bottom: 20px;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Header
# -----------------------------
st.title("Amazon Transportation Survey Dashboard")
st.caption("Ben Franklin Transit | Employee Commute and Transportation Needs Analysis")

uploaded_file = st.sidebar.file_uploader(
    "Upload cleaned Excel file",
    type=["xlsx"]
)

if uploaded_file is None:
    st.info("Upload your cleaned Excel file to begin.")
    st.stop()

xls = pd.ExcelFile(uploaded_file)

cleaned_data = pd.read_excel(uploaded_file, sheet_name="cleaned_data")
question_lookup = pd.read_excel(uploaded_file, sheet_name="question_lookup")

question_dict = dict(zip(question_lookup["question_id"], question_lookup["question_text"]))

# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Choose a section",
    [
        "Dashboard Overview",
        "Question Analysis",
        "Open-Ended Themes",
        "Relationship Analysis",
        "Data Explorer"
    ]
)

# -----------------------------
# Overview Page
# -----------------------------
if page == "Dashboard Overview":

    st.subheader("Survey Overview")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Total Responses</div>
            <div class="metric-value">{len(cleaned_data)}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Survey Questions</div>
            <div class="metric-value">{len(question_lookup)}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Dashboard Sheets</div>
            <div class="metric-value">{len(xls.sheet_names)}</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        missing_rate = round(cleaned_data.isna().mean().mean() * 100, 1)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Average Missing Data</div>
            <div class="metric-value">{missing_rate}%</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    st.subheader("Purpose of the Dashboard")
    st.markdown("""
    This dashboard summarizes employee transportation survey results from the Amazon facility.
    It is designed to help identify commute patterns, transportation barriers, interest in transit,
    and possible opportunities for service planning, employer partnerships, carpool/vanpool programs,
    and access improvements.
    """)

    st.subheader("Survey Questions")
    st.dataframe(question_lookup, use_container_width=True)

# -----------------------------
# Question Analysis
# -----------------------------
elif page == "Question Analysis":

    st.subheader("Question-by-Question Analysis")

    selected_q = st.selectbox(
        "Select a survey question",
        question_lookup["question_id"],
        format_func=lambda q: f"{q} — {question_dict[q]}"
    )

    st.markdown(f"### {selected_q}: {question_dict[selected_q]}")

    q_data = cleaned_data[selected_q].dropna().astype(str)

    if q_data.empty:
        st.warning("No responses available for this question.")
        st.stop()

    summary = q_data.value_counts().reset_index()
    summary.columns = ["Response", "Count"]
    summary["Percent"] = round(summary["Count"] / summary["Count"].sum() * 100, 1)

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("#### Response Summary")
        st.dataframe(summary, use_container_width=True)

    with col2:
        fig = px.bar(
            summary,
            x="Count",
            y="Response",
            orientation="h",
            text="Percent",
            title="Response Distribution"
        )
        fig.update_traces(texttemplate="%{text}%")
        fig.update_layout(
            height=500,
            margin=dict(l=20, r=20, t=60, b=20),
            yaxis=dict(categoryorder="total ascending")
        )
        st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# Open-Ended Themes
# -----------------------------
elif page == "Open-Ended Themes":

    st.subheader("Open-Ended Response Themes")

    if "theme_summary" not in xls.sheet_names or "open_ended_themes" not in xls.sheet_names:
        st.warning("Theme analysis sheets were not found.")
        st.stop()

    theme_summary = pd.read_excel(uploaded_file, sheet_name="theme_summary")
    open_responses = pd.read_excel(uploaded_file, sheet_name="open_ended_themes")

    selected_open_q = st.selectbox(
        "Select an open-ended question",
        theme_summary["question_id"].unique()
    )

    if selected_open_q in question_dict:
        st.markdown(f"### {selected_open_q}: {question_dict[selected_open_q]}")

    filtered_theme = theme_summary[theme_summary["question_id"] == selected_open_q]
    filtered_responses = open_responses[open_responses["question_id"] == selected_open_q]

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("#### Theme Counts")
        st.dataframe(filtered_theme, use_container_width=True)

    with col2:
        fig = px.bar(
            filtered_theme.sort_values("count"),
            x="count",
            y="theme",
            orientation="h",
            text="count",
            title="Main Themes"
        )
        fig.update_layout(height=450)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Open-Ended Responses")

    search_term = st.text_input("Search within responses")

    if search_term:
        filtered_responses = filtered_responses[
            filtered_responses["response_text"]
            .astype(str)
            .str.contains(search_term, case=False, na=False)
        ]

    st.dataframe(filtered_responses, use_container_width=True)

# -----------------------------
# Relationship Analysis
# -----------------------------
elif page == "Relationship Analysis":

    st.subheader("Relationship Between Survey Questions")

    st.markdown("""
    Use this section to compare how answers to one question relate to another.
    For example, you can compare commute mode with interest in transit, or shift time with transportation barriers.
    """)

    question_ids = list(question_lookup["question_id"])

    col1, col2 = st.columns(2)

    with col1:
        q1 = st.selectbox(
            "First question",
            question_ids,
            format_func=lambda q: f"{q} — {question_dict[q]}"
        )

    with col2:
        q2 = st.selectbox(
            "Second question",
            question_ids,
            index=1 if len(question_ids) > 1 else 0,
            format_func=lambda q: f"{q} — {question_dict[q]}"
        )

    if q1 == q2:
        st.warning("Please select two different questions.")
    else:
        relationship_table = pd.crosstab(
            cleaned_data[q1].astype(str),
            cleaned_data[q2].astype(str)
        )

        st.markdown("#### Cross-Tabulation")
        st.dataframe(relationship_table, use_container_width=True)

        heatmap_data = relationship_table.reset_index().melt(
            id_vars=q1,
            var_name=q2,
            value_name="Count"
        )

        fig = px.density_heatmap(
            heatmap_data,
            x=q2,
            y=q1,
            z="Count",
            title="Relationship Heatmap"
        )

        fig.update_layout(height=600)
        st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# Data Explorer
# -----------------------------
elif page == "Data Explorer":

    st.subheader("Cleaned Survey Data")

    st.dataframe(cleaned_data, use_container_width=True)

    csv = cleaned_data.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Download cleaned data as CSV",
        data=csv,
        file_name="cleaned_amazon_survey.csv",
        mime="text/csv"
    )
