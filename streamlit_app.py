
import streamlit as st
import pandas as pd
import plotly.express as px
import re
from collections import Counter

# Optional word cloud support
try:
    from wordcloud import WordCloud, STOPWORDS
    import matplotlib.pyplot as plt
    WORDCLOUD_AVAILABLE = True
except Exception:
    WORDCLOUD_AVAILABLE = False

st.set_page_config(
    page_title="Amazon Transportation Survey Dashboard",
    layout="wide"
)

# --------------------------------------------------
# Design / colors
# --------------------------------------------------
COLOR_SEQUENCE = [
    "#006BA6", "#2E8B57", "#F28E2B", "#7A5195",
    "#D45087", "#4E79A7", "#59A14F", "#E15759",
    "#76B7B2", "#EDC948"
]

st.markdown("""
<style>
.block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
    max-width: 1450px;
}
.main {
    background-color: #f6f8fb;
}
h1, h2, h3 {
    letter-spacing: -0.03em;
}
.dashboard-header {
    background: linear-gradient(120deg, #17324d 0%, #006BA6 55%, #2E8B57 100%);
    padding: 28px 32px;
    border-radius: 22px;
    color: white;
    margin-bottom: 22px;
    box-shadow: 0 8px 24px rgba(16,24,40,.14);
}
.dashboard-title {
    font-size: 2.2rem;
    font-weight: 800;
    margin-bottom: 4px;
}
.dashboard-subtitle {
    font-size: 1rem;
    opacity: .92;
}
.kpi-card {
    background: #ffffff;
    border: 1px solid #e6eaf0;
    border-radius: 18px;
    padding: 20px 22px;
    box-shadow: 0 4px 14px rgba(16,24,40,.06);
    min-height: 128px;
}
.kpi-label {
    font-size: .78rem;
    color: #667085;
    text-transform: uppercase;
    letter-spacing: .08em;
    font-weight: 700;
}
.kpi-value {
    font-size: 2rem;
    font-weight: 800;
    color: #17324d;
    margin-top: 8px;
}
.kpi-note {
    font-size: .88rem;
    color: #667085;
    margin-top: 6px;
}
.section-card {
    background: white;
    border: 1px solid #e6eaf0;
    border-radius: 18px;
    padding: 22px;
    box-shadow: 0 4px 14px rgba(16,24,40,.045);
    margin-bottom: 18px;
}
.insight-card {
    background: #ffffff;
    border-left: 5px solid #006BA6;
    border-radius: 16px;
    padding: 16px 18px;
    box-shadow: 0 3px 12px rgba(16,24,40,.05);
    margin-bottom: 12px;
}
.insight-title {
    font-weight: 800;
    color: #17324d;
    margin-bottom: 4px;
}
.insight-body {
    color: #475467;
    font-size: .94rem;
}
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
}
.stTabs [data-baseweb="tab"] {
    background-color: #ffffff;
    border-radius: 12px 12px 0 0;
    padding: 12px 18px;
    border: 1px solid #e6eaf0;
}
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------
# Helper functions
# --------------------------------------------------
def kpi_card(label, value, note=""):
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def insight_card(title, body):
    st.markdown(
        f"""
        <div class="insight-card">
            <div class="insight-title">{title}</div>
            <div class="insight-body">{body}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def split_multi_response(value):
    """Split multi-select responses. Main separator in this survey appears to be semicolon."""
    if pd.isna(value):
        return []
    text = str(value).strip()
    if not text:
        return []
    parts = re.split(r";|\n|\|", text)
    return [p.strip() for p in parts if p.strip()]


def summarize_single(df, col, label="Response"):
    data = df[col].dropna().astype(str).str.strip()
    data = data[data != ""]
    summary = data.value_counts().reset_index()
    summary.columns = [label, "Count"]
    if summary["Count"].sum() > 0:
        summary["Percent"] = (summary["Count"] / summary["Count"].sum() * 100).round(1)
    else:
        summary["Percent"] = 0
    return summary


def summarize_multi(df, col):
    items = []
    for value in df[col]:
        items.extend(split_multi_response(value))
    if not items:
        return pd.DataFrame(columns=["Option", "Count", "Percent of respondents"])
    summary = pd.Series(items).value_counts().reset_index()
    summary.columns = ["Option", "Count"]
    summary["Percent of respondents"] = (summary["Count"] / max(len(df), 1) * 100).round(1)
    return summary


def extract_first_number(value):
    if pd.isna(value):
        return None
    text = str(value).lower().replace(",", ".")
    nums = re.findall(r"\d+(?:\.\d+)?", text)
    if not nums:
        return None
    values = [float(n) for n in nums]
    return sum(values) / len(values) if len(values) > 1 else values[0]


def minute_range(value):
    n = extract_first_number(value)
    if n is None:
        return "No response / unclear"
    if n <= 10:
        return "0–10 minutes"
    elif n <= 20:
        return "11–20 minutes"
    elif n <= 30:
        return "21–30 minutes"
    elif n <= 45:
        return "31–45 minutes"
    elif n <= 60:
        return "46–60 minutes"
    else:
        return "More than 60 minutes"


def mile_range(value):
    n = extract_first_number(value)
    if n is None:
        return "No response / unclear"
    if n <= 2:
        return "0–2 miles"
    elif n <= 5:
        return "3–5 miles"
    elif n <= 10:
        return "6–10 miles"
    elif n <= 15:
        return "11–15 miles"
    elif n <= 25:
        return "16–25 miles"
    else:
        return "More than 25 miles"


def cost_range(value):
    n = extract_first_number(value)
    if n is None:
        return "No response / unclear"
    if n == 0:
        return "$0"
    elif n <= 5:
        return "$1–$5"
    elif n <= 10:
        return "$6–$10"
    elif n <= 20:
        return "$11–$20"
    elif n <= 30:
        return "$21–$30"
    else:
        return "More than $30"


def summarize_range(df, col, range_func, range_label):
    temp = df[col].apply(range_func)
    summary = temp.value_counts().reset_index()
    summary.columns = [range_label, "Count"]
    summary["Percent"] = (summary["Count"] / max(summary["Count"].sum(), 1) * 100).round(1)
    return summary


def theme_tags(text):
    if pd.isna(text):
        return []
    t = str(text).lower()
    themes = {
        "Earlier / later service": [
            "early", "earlier", "late", "later", "night", "morning",
            "5 de la mañana", "madrugada", "temprano", "tarde"
        ],
        "Schedule alignment": [
            "schedule", "shift", "work hours", "hour", "horario", "entrada", "salida",
            "time", "tiempo"
        ],
        "More frequent service": [
            "frequency", "frequent", "more buses", "every", "frecuencia", "frecuente"
        ],
        "Better routes / coverage": [
            "route", "routes", "ruta", "rutas", "coverage", "direct", "transfer",
            "connection", "near", "stop", "parada"
        ],
        "Cost / subsidy": [
            "cost", "free", "fare", "pass", "subsidy", "discount", "gas", "money",
            "pagar", "gratis", "costo", "dollars"
        ],
        "Reliability": [
            "reliable", "on time", "delay", "delayed", "late", "reliability", "puntual"
        ],
        "Safety / comfort": [
            "safe", "safety", "dark", "danger", "comfort", "comfortable", "seguro",
            "seguridad"
        ],
        "Carpool / rideshare / vanpool": [
            "carpool", "rideshare", "ride share", "vanpool", "shared ride"
        ],
        "Employer coordination": [
            "company", "amazon", "work", "employee", "employer", "coordinating",
            "coordinando"
        ],
    }
    found = []
    for theme, words in themes.items():
        if any(w in t for w in words):
            found.append(theme)
    return found if found else ["Other / needs review"]


def theme_summary_for_question(df, col):
    rows = []
    for response in df[col].dropna().astype(str):
        for theme in theme_tags(response):
            rows.append({"Theme": theme, "Response": response})
    theme_df = pd.DataFrame(rows)
    if theme_df.empty:
        return pd.DataFrame(columns=["Theme", "Count", "Percent of responses"]), pd.DataFrame(columns=["Theme", "Response"])
    summary = theme_df["Theme"].value_counts().reset_index()
    summary.columns = ["Theme", "Count"]
    response_count = df[col].dropna().shape[0]
    summary["Percent of responses"] = (summary["Count"] / max(response_count, 1) * 100).round(1)
    return summary, theme_df


def clean_words(text_series):
    extra_stopwords = {
        "nan", "none", "na", "n/a", "not", "required", "please", "would", "could",
        "work", "transportation", "public", "bus", "buses", "route", "routes",
        "use", "using", "get", "make", "need", "needs", "answer", "question",
        "company", "amazon", "employee", "employees", "para", "que", "los", "las",
        "una", "uno", "con", "por", "del", "como", "más", "mas", "hay", "trabajo",
        "salida", "entrada"
    }
    all_text = " ".join(text_series.dropna().astype(str).tolist()).lower()
    all_text = re.sub(r"[^a-zA-ZáéíóúñüÁÉÍÓÚÑÜ\s]", " ", all_text)
    words = [w.strip() for w in all_text.split() if len(w.strip()) > 2]
    words = [w for w in words if w not in extra_stopwords]
    return Counter(words)


def show_wordcloud(text_series, title):
    st.markdown(f"#### {title}")
    word_counts = clean_words(text_series)

    if not word_counts:
        st.info("No words available for this word cloud.")
        return

    if WORDCLOUD_AVAILABLE:
        wc = WordCloud(
            width=1100,
            height=520,
            background_color="white",
            colormap="viridis",
            max_words=120,
            collocations=False
        ).generate_from_frequencies(word_counts)

        fig, ax = plt.subplots(figsize=(12, 5.5))
        ax.imshow(wc, interpolation="bilinear")
        ax.axis("off")
        st.pyplot(fig)
    else:
        # Fallback if wordcloud is not installed
        top_words = pd.DataFrame(word_counts.most_common(25), columns=["Word", "Count"])
        fig = px.bar(
            top_words.sort_values("Count"),
            x="Count",
            y="Word",
            orientation="h",
            color="Count",
            color_continuous_scale="Viridis",
            title="Top repeated words"
        )
        fig.update_layout(height=520)
        st.plotly_chart(fig, use_container_width=True)


def prettify_question(qid, question_dict):
    return f"{qid} — {question_dict.get(qid, qid)}"


def plot_bar(summary, x, y, title, orientation="h", text_col=None, color_col=None, height=470):
    fig = px.bar(
        summary,
        x=x,
        y=y,
        orientation=orientation,
        text=text_col,
        color=color_col if color_col else y,
        color_discrete_sequence=COLOR_SEQUENCE,
        color_continuous_scale="Viridis",
        title=title
    )
    if text_col:
        fig.update_traces(texttemplate="%{text}")
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=60, b=10),
        showlegend=False
    )
    if orientation == "h":
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
    return fig


def transform_question_series(df, qid):
    if qid == "Q3":
        return df[qid].apply(minute_range)
    if qid == "Q4":
        return df[qid].apply(mile_range)
    if qid == "Q20":
        return df[qid].apply(cost_range)
    return df[qid].astype(str)


def explode_if_multiselect(df, qid):
    if qid in ["Q6", "Q9", "Q14"]:
        rows = []
        for _, row in df.iterrows():
            for item in split_multi_response(row[qid]):
                new_row = row.copy()
                new_row[qid] = item
                rows.append(new_row)
        return pd.DataFrame(rows) if rows else df.iloc[0:0].copy()
    return df.copy()


# --------------------------------------------------
# Load data
# --------------------------------------------------
st.markdown(
    """
    <div class="dashboard-header">
        <div class="dashboard-title">Amazon Transportation Survey Dashboard</div>
        <div class="dashboard-subtitle">Ben Franklin Transit | Commute behavior, transit barriers, and employer transportation opportunities</div>
    </div>
    """,
    unsafe_allow_html=True
)

uploaded_file = st.sidebar.file_uploader("Upload cleaned Excel file", type=["xlsx"])

if uploaded_file is None:
    st.info("Upload your cleaned Excel file to begin.")
    st.stop()

xls = pd.ExcelFile(uploaded_file)
cleaned_data = pd.read_excel(uploaded_file, sheet_name="cleaned_data")
question_lookup = pd.read_excel(uploaded_file, sheet_name="question_lookup")
question_dict = dict(zip(question_lookup["question_id"], question_lookup["question_text"]))

# Ensure Q columns exist
available_qs = [q for q in question_lookup["question_id"].tolist() if q in cleaned_data.columns]

# Sidebar filters
st.sidebar.header("Filters")
filtered_data = cleaned_data.copy()

if "Q2" in cleaned_data.columns:
    mode_options = sorted(cleaned_data["Q2"].dropna().astype(str).unique())
    selected_modes = st.sidebar.multiselect("Primary commute mode", mode_options, default=mode_options)
    if selected_modes:
        filtered_data = filtered_data[filtered_data["Q2"].astype(str).isin(selected_modes)]

if "Q5" in cleaned_data.columns:
    pt_options = sorted(cleaned_data["Q5"].dropna().astype(str).unique())
    selected_pt = st.sidebar.multiselect("Public transportation use", pt_options, default=pt_options)
    if selected_pt:
        filtered_data = filtered_data[filtered_data["Q5"].astype(str).isin(selected_pt)]

st.sidebar.caption(f"Showing {len(filtered_data)} of {len(cleaned_data)} responses")

# --------------------------------------------------
# Top KPI logic
# --------------------------------------------------
total_responses = len(filtered_data)

open_to_change = "N/A"
if "Q8" in filtered_data.columns:
    q8 = filtered_data["Q8"].dropna().astype(str).str.lower()
    open_to_change = f"{q8.isin(['yes', 'maybe']).mean() * 100:.0f}%"

pass_interest = "N/A"
if "Q15" in filtered_data.columns:
    q15 = filtered_data["Q15"].dropna().astype(str).str.lower()
    pass_interest = f"{q15.isin(['likely', 'very likely']).mean() * 100:.0f}%"

program_interest = "N/A"
if "Q16" in filtered_data.columns:
    q16 = filtered_data["Q16"].dropna().astype(str).str.lower()
    program_interest = f"{q16.isin(['likely', 'very likely']).mean() * 100:.0f}%"

main_barrier = "N/A"
if "Q9" in filtered_data.columns:
    q9_summary = summarize_multi(filtered_data, "Q9")
    if not q9_summary.empty:
        main_barrier = q9_summary.iloc[0]["Option"]

# --------------------------------------------------
# Tabs: no Data Explorer tab
# --------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "1. Executive Overview",
    "2. Question Analysis",
    "3. Transit Barriers",
    "4. Open-Ended Themes",
    "5. Relationships"
])

# --------------------------------------------------
# Tab 1: Executive Overview
# Q10 is allowed here only
# --------------------------------------------------
with tab1:
    st.subheader("Executive Overview")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Survey responses", total_responses, "Filtered responses")
    with c2:
        kpi_card("Open to changing mode", open_to_change, "Yes or maybe")
    with c3:
        kpi_card("Transit pass interest", pass_interest, "Likely or very likely")
    with c4:
        kpi_card("Program interest", program_interest, "Company pass/carpool/rideshare")

    st.markdown("---")

    left, right = st.columns([1.2, .8])

    with left:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("### Primary Commute Mode")
        if "Q2" in filtered_data.columns:
            mode_summary = summarize_single(filtered_data, "Q2", "Mode")
            fig = plot_bar(
                mode_summary,
                x="Count",
                y="Mode",
                title="How employees currently get to work",
                text_col="Percent",
                color_col="Mode",
                height=430
            )
            fig.update_traces(texttemplate="%{text}%")
            st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("### Planning Insights")
        insight_card(
            "Main reported barrier",
            f"The most frequently selected reason for not using public transportation is: <b>{main_barrier}</b>."
        )
        insight_card(
            "Most useful dashboard question",
            "The key planning question is not only who uses transit today, but who may shift modes if schedule, access, cost, and reliability barriers are addressed."
        )
        insight_card(
            "Employer partnership opportunity",
            "Compare interest in subsidized passes with carpool/rideshare programs to identify which strategy may work best for Amazon employees."
        )
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("### Planning Location Reference: Q10")
    if "Q10" in filtered_data.columns:
        st.caption("Q10 is shown only in this overview tab, as requested.")
        q10_summary = summarize_single(filtered_data, "Q10", "Nearest cross street")
        st.dataframe(q10_summary.head(25), use_container_width=True)
    else:
        st.info("Q10 was not found in the cleaned data.")

# --------------------------------------------------
# Tab 2: Question Analysis
# Q1 removed, Q10 removed, Q3/Q4/Q20 as ranges, Q6/Q9/Q14 as multi-select
# --------------------------------------------------
with tab2:
    st.subheader("Question-by-Question Analysis")

    excluded_questions = ["Q1", "Q10"]
    question_options = [q for q in available_qs if q not in excluded_questions]

    selected_q = st.selectbox(
        "Select a survey question",
        question_options,
        format_func=lambda q: prettify_question(q, question_dict)
    )

    st.markdown(f"### {prettify_question(selected_q, question_dict)}")

    if selected_q == "Q3":
        summary = summarize_range(filtered_data, "Q3", minute_range, "Commute time range")
        x_col, y_col = "Count", "Commute time range"
        title = "Typical commute time grouped into ranges"

    elif selected_q == "Q4":
        summary = summarize_range(filtered_data, "Q4", mile_range, "Commute distance range")
        x_col, y_col = "Count", "Commute distance range"
        title = "Commute distance grouped into ranges"

    elif selected_q == "Q20":
        summary = summarize_range(filtered_data, "Q20", cost_range, "Daily commute cost range")
        x_col, y_col = "Count", "Daily commute cost range"
        title = "Daily commute cost grouped into ranges"

    elif selected_q in ["Q6", "Q9", "Q14"]:
        summary = summarize_multi(filtered_data, selected_q)
        x_col, y_col = "Count", "Option"
        title = "Each selected option counted separately"

    else:
        summary = summarize_single(filtered_data, selected_q, "Response")
        x_col, y_col = "Count", "Response"
        title = "Response distribution"

    col1, col2 = st.columns([.95, 1.65])

    with col1:
        st.markdown("#### Summary Table")
        st.dataframe(summary, use_container_width=True)

    with col2:
        if not summary.empty:
            text_col = "Percent" if "Percent" in summary.columns else "Percent of respondents"
            fig = plot_bar(
                summary,
                x=x_col,
                y=y_col,
                title=title,
                text_col=text_col,
                color_col=y_col,
                height=560
            )
            suffix = "%" if "Percent" in text_col else "%"
            fig.update_traces(texttemplate="%{text}%")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No responses available for this question.")

# --------------------------------------------------
# Tab 3: Transit Barriers
# Q6/Q9/Q14 count repeated options separately
# --------------------------------------------------
with tab3:
    st.subheader("Transit Barriers and Motivators")

    col1, col2 = st.columns(2)

    with col1:
        if "Q6" in filtered_data.columns:
            st.markdown("### Q6. Current Transportation Challenges")
            q6_summary = summarize_multi(filtered_data, "Q6")
            fig = plot_bar(
                q6_summary,
                x="Count",
                y="Option",
                title="How many times each challenge was selected",
                text_col="Percent of respondents",
                color_col="Option",
                height=520
            )
            fig.update_traces(texttemplate="%{text}%")
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        if "Q9" in filtered_data.columns:
            st.markdown("### Q9. Main Reasons for Not Using Transit")
            q9_summary = summarize_multi(filtered_data, "Q9")
            fig = plot_bar(
                q9_summary,
                x="Count",
                y="Option",
                title="How many times each reason was selected",
                text_col="Percent of respondents",
                color_col="Option",
                height=520
            )
            fig.update_traces(texttemplate="%{text}%")
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Q14. What Would Motivate More Public Transportation Use?")
    if "Q14" in filtered_data.columns:
        q14_summary = summarize_multi(filtered_data, "Q14")
        fig = plot_bar(
            q14_summary,
            x="Count",
            y="Option",
            title="Motivators selected by respondents",
            text_col="Percent of respondents",
            color_col="Option",
            height=560
        )
        fig.update_traces(texttemplate="%{text}%")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.markdown("### Supporting Planning Factors")

    c1, c2, c3 = st.columns(3)
    for qid, title, container in [
        ("Q11", "Distance to Nearest Stop"),
        ("Q12", "Reliability"),
        ("Q13", "Safety"),
    ]:
        pass

    supporting = [("Q11", "Distance to nearest stop"), ("Q12", "Reliability"), ("Q13", "Safety")]
    containers = st.columns(3)

    for (qid, title), container in zip(supporting, containers):
        with container:
            if qid in filtered_data.columns:
                st.markdown(f"#### {title}")
                summary = summarize_single(filtered_data, qid, "Response")
                fig = px.bar(
                    summary,
                    x="Response",
                    y="Count",
                    text="Percent",
                    color="Response",
                    color_discrete_sequence=COLOR_SEQUENCE
                )
                fig.update_traces(texttemplate="%{text}%")
                fig.update_layout(height=340, showlegend=False, margin=dict(l=10, r=10, t=20, b=10))
                st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# Tab 4: Open-ended themes and word clouds
# Q18, Q24, Q25 as themes + word clouds
# --------------------------------------------------
with tab4:
    st.subheader("Open-Ended Theme and Word Analysis")

    open_questions = [q for q in ["Q18", "Q24", "Q25"] if q in filtered_data.columns]

    selected_open_q = st.selectbox(
        "Select open-ended question",
        open_questions,
        format_func=lambda q: prettify_question(q, question_dict)
    )

    st.markdown(f"### {prettify_question(selected_open_q, question_dict)}")

    theme_summary, response_theme_df = theme_summary_for_question(filtered_data, selected_open_q)

    col1, col2 = st.columns([1, 1.4])

    with col1:
        st.markdown("#### Theme Summary")
        st.dataframe(theme_summary, use_container_width=True)

        if not theme_summary.empty:
            fig = plot_bar(
                theme_summary,
                x="Count",
                y="Theme",
                title="Main themes identified in responses",
                text_col="Percent of responses",
                color_col="Theme",
                height=500
            )
            fig.update_traces(texttemplate="%{text}%")
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        show_wordcloud(filtered_data[selected_open_q], "Word Map / Word Cloud")

    st.markdown("### Open-Ended Responses")
    selected_theme = "All"
    if not theme_summary.empty:
        selected_theme = st.selectbox("Filter responses by theme", ["All"] + theme_summary["Theme"].tolist())

    responses_display = response_theme_df.copy()
    if selected_theme != "All":
        responses_display = responses_display[responses_display["Theme"] == selected_theme]

    search_text = st.text_input("Search responses")
    if search_text:
        responses_display = responses_display[
            responses_display["Response"].astype(str).str.contains(search_text, case=False, na=False)
        ]

    st.dataframe(responses_display, use_container_width=True, height=420)

# --------------------------------------------------
# Tab 5: Relationship analysis
# Q1 and Q10 removed from relationship analysis
# Q3/Q4/Q20 transformed as ranges
# Q6/Q9/Q14 can be exploded if selected
# --------------------------------------------------
with tab5:
    st.subheader("Relationship Analysis")

    st.markdown(
        """
        Use this section to compare survey answers. Q1 and Q10 are excluded here.
        Q3, Q4, and Q20 are grouped into ranges, and Q6, Q9, and Q14 are treated as multi-select questions.
        """
    )

    relationship_questions = [q for q in available_qs if q not in ["Q1", "Q10"]]

    col1, col2 = st.columns(2)

    with col1:
        q_row = st.selectbox(
            "Rows",
            relationship_questions,
            format_func=lambda q: prettify_question(q, question_dict),
            index=0
        )

    with col2:
        q_col = st.selectbox(
            "Columns",
            relationship_questions,
            format_func=lambda q: prettify_question(q, question_dict),
            index=1 if len(relationship_questions) > 1 else 0
        )

    if q_row == q_col:
        st.warning("Please select two different questions.")
    else:
        temp = filtered_data.copy()

        # For multi-select questions, explode one or both sides.
        if q_row in ["Q6", "Q9", "Q14"]:
            temp = explode_if_multiselect(temp, q_row)
        if q_col in ["Q6", "Q9", "Q14"]:
            temp = explode_if_multiselect(temp, q_col)

        if temp.empty:
            st.info("There is not enough data to create this relationship.")
        else:
            row_series = transform_question_series(temp, q_row)
            col_series = transform_question_series(temp, q_col)

            rel_df = pd.DataFrame({
                "Row Question": row_series,
                "Column Question": col_series
            }).dropna()

            rel_df = rel_df[
                (rel_df["Row Question"].astype(str).str.strip() != "") &
                (rel_df["Column Question"].astype(str).str.strip() != "")
            ]

            cross_tab = pd.crosstab(rel_df["Row Question"], rel_df["Column Question"])

            st.markdown("#### Cross-Tabulation")
            st.dataframe(cross_tab, use_container_width=True)

            heatmap_data = cross_tab.reset_index().melt(
                id_vars="Row Question",
                var_name="Column Question",
                value_name="Count"
            )

            fig = px.density_heatmap(
                heatmap_data,
                x="Column Question",
                y="Row Question",
                z="Count",
                text_auto=True,
                color_continuous_scale="YlGnBu",
                title="Relationship Heatmap"
            )
            fig.update_layout(height=650, margin=dict(l=10, r=10, t=60, b=20))
            st.plotly_chart(fig, use_container_width=True)

            insight_card(
                "How to interpret this chart",
                "Look for higher-count cells where transportation needs overlap with willingness, interest, or barriers. These intersections are the most useful for service planning and employer partnership decisions."
            )
