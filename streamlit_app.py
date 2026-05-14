
import streamlit as st
import pandas as pd
import plotly.express as px
import re
from collections import Counter
import html

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
.word-map {
    background-color: white;
    border-radius: 14px;
    padding: 22px;
    box-shadow: 0px 2px 8px rgba(0,0,0,0.06);
    line-height: 2.6;
}
.word-chip {
    display: inline-block;
    margin: 6px 10px 6px 0;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

COLOR_SEQUENCE = [
    "#1f77b4", "#2ca02c", "#ff7f0e", "#9467bd", "#d62728",
    "#17becf", "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22"
]

# -----------------------------
# Helper Functions
# -----------------------------
def split_multi_response(value):
    """For select-all-that-apply questions such as Q6, Q9, and Q14."""
    if pd.isna(value):
        return []
    text = str(value).strip()
    if not text:
        return []
    parts = re.split(r";|\n|\|", text)
    return [p.strip() for p in parts if p.strip()]


def summarize_single(series):
    summary = (
        series.dropna()
        .astype(str)
        .str.strip()
        .replace("", pd.NA)
        .dropna()
        .value_counts()
        .reset_index()
    )
    summary.columns = ["Response", "Count"]
    summary["Percent"] = round(summary["Count"] / summary["Count"].sum() * 100, 1)
    return summary


def summarize_multi(series, total_respondents):
    all_items = []
    for value in series.dropna():
        all_items.extend(split_multi_response(value))

    if not all_items:
        return pd.DataFrame(columns=["Response", "Count", "Percent of Respondents"])

    summary = pd.Series(all_items).value_counts().reset_index()
    summary.columns = ["Response", "Count"]
    summary["Percent of Respondents"] = round(summary["Count"] / max(total_respondents, 1) * 100, 1)
    return summary


def extract_number(value):
    if pd.isna(value):
        return None

    text = str(value).lower().replace(",", ".")
    nums = re.findall(r"\d+(?:\.\d+)?", text)

    if not nums:
        return None

    nums = [float(n) for n in nums]

    # If a person wrote a range like 20-30, use the average.
    if len(nums) >= 2:
        return sum(nums[:2]) / 2

    return nums[0]


def commute_time_range(value):
    n = extract_number(value)
    if n is None:
        return "Unclear / no response"
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


def commute_distance_range(value):
    n = extract_number(value)
    if n is None:
        return "Unclear / no response"
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


def commute_cost_range(value):
    n = extract_number(value)
    if n is None:
        return "Unclear / no response"
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


def summarize_range(series, range_function):
    ranged = series.apply(range_function)
    return summarize_single(ranged)


def detect_themes(text):
    if pd.isna(text):
        return []

    text = str(text).lower()

    theme_keywords = {
        "Schedule alignment": [
            "schedule", "shift", "work hours", "hour", "time", "horario",
            "entrada", "salida", "turno"
        ],
        "Earlier or later service": [
            "early", "earlier", "late", "later", "night", "morning",
            "madrugada", "temprano", "tarde"
        ],
        "More frequent service": [
            "frequency", "frequent", "more buses", "often", "every",
            "frecuencia", "frecuente"
        ],
        "Better routes or coverage": [
            "route", "routes", "direct", "transfer", "connection", "coverage",
            "near", "stop", "ruta", "rutas", "parada"
        ],
        "Cost or subsidy": [
            "cost", "free", "fare", "pass", "subsidy", "discount", "gas",
            "money", "costo", "gratis", "pagar"
        ],
        "Reliability": [
            "reliable", "reliability", "on time", "delay", "delayed",
            "puntual"
        ],
        "Safety or comfort": [
            "safe", "safety", "dark", "danger", "comfortable", "comfort",
            "seguro", "seguridad"
        ],
        "Carpool, rideshare, or vanpool": [
            "carpool", "rideshare", "ride share", "vanpool", "shared ride"
        ],
        "Employer support": [
            "company", "amazon", "employer", "employee", "work",
            "empresa", "compañía"
        ]
    }

    found = []
    for theme, keywords in theme_keywords.items():
        if any(keyword in text for keyword in keywords):
            found.append(theme)

    if not found:
        found.append("Other / review")

    return found


def create_theme_outputs(df, qid):
    rows = []

    for response in df[qid].dropna().astype(str):
        themes = detect_themes(response)
        for theme in themes:
            rows.append({
                "Question": qid,
                "Theme": theme,
                "Response": response
            })

    theme_df = pd.DataFrame(rows)

    if theme_df.empty:
        theme_summary = pd.DataFrame(columns=["Theme", "Count", "Percent"])
    else:
        theme_summary = theme_df["Theme"].value_counts().reset_index()
        theme_summary.columns = ["Theme", "Count"]
        total_responses = df[qid].dropna().shape[0]
        theme_summary["Percent"] = round(theme_summary["Count"] / max(total_responses, 1) * 100, 1)

    return theme_summary, theme_df


def word_counts(series):
    stop_words = {
        "the", "and", "for", "that", "this", "with", "from", "have", "has",
        "are", "was", "were", "you", "your", "will", "would", "could", "should",
        "not", "but", "can", "all", "our", "their", "they", "them", "than",
        "then", "also", "more", "very", "use", "using", "used", "need", "needs",
        "work", "transportation", "public", "bus", "buses", "route", "routes",
        "amazon", "company", "employee", "employees", "commute", "answer",
        "none", "nan", "n/a", "na", "para", "que", "los", "las", "una", "uno",
        "con", "por", "del", "como", "mas", "más", "hay", "trabajo"
    }

    text = " ".join(series.dropna().astype(str)).lower()
    text = re.sub(r"[^a-zA-ZáéíóúñüÁÉÍÓÚÑÜ\s]", " ", text)
    words = [w.strip() for w in text.split() if len(w.strip()) > 2]
    words = [w for w in words if w not in stop_words]

    return Counter(words)


def show_word_map(series):
    counts = word_counts(series)

    if not counts:
        st.info("No words available for the word map.")
        return

    top_words = counts.most_common(45)
    max_count = max(count for word, count in top_words)

    colors = COLOR_SEQUENCE
    html_parts = []

    for i, (word, count) in enumerate(top_words):
        size = 14 + int((count / max_count) * 28)
        color = colors[i % len(colors)]
        safe_word = html.escape(word)
        html_parts.append(
            f'<span class="word-chip" style="font-size:{size}px;color:{color};" title="{count} times">{safe_word}</span>'
        )

    st.markdown(
        f"""
        <div class="word-map">
            {" ".join(html_parts)}
        </div>
        """,
        unsafe_allow_html=True
    )


def plot_horizontal_bar(summary, y_col="Response", percent_col="Percent", title="Response Distribution"):
    fig = px.bar(
        summary,
        x="Count",
        y=y_col,
        orientation="h",
        text=percent_col,
        color=y_col,
        color_discrete_sequence=COLOR_SEQUENCE,
        title=title
    )

    fig.update_traces(texttemplate="%{text}%")
    fig.update_layout(
        height=520,
        margin=dict(l=20, r=20, t=60, b=20),
        yaxis=dict(categoryorder="total ascending"),
        showlegend=False
    )

    return fig


def transformed_series_for_relationship(df, qid):
    if qid == "Q3":
        return df[qid].apply(commute_time_range)
    elif qid == "Q4":
        return df[qid].apply(commute_distance_range)
    elif qid == "Q20":
        return df[qid].apply(commute_cost_range)
    else:
        return df[qid].astype(str)


def explode_multiselect_for_relationship(df, qid):
    if qid not in ["Q6", "Q9", "Q14"]:
        return df

    rows = []
    for _, row in df.iterrows():
        items = split_multi_response(row[qid])
        if not items:
            continue
        for item in items:
            new_row = row.copy()
            new_row[qid] = item
            rows.append(new_row)

    if not rows:
        return df.iloc[0:0].copy()

    return pd.DataFrame(rows)


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
        "Relationship Analysis"
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
        # Q1 is not useful as an analytical question, so subtract it from the count.
        analytical_questions = question_lookup[~question_lookup["question_id"].isin(["Q1"])]
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Analytical Questions</div>
            <div class="metric-value">{len(analytical_questions)}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        if "Q8" in cleaned_data.columns:
            open_to_change = cleaned_data["Q8"].dropna().astype(str).str.lower().isin(["yes", "maybe"]).mean() * 100
            value = f"{open_to_change:.0f}%"
        else:
            value = "N/A"

        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Open to Changing Mode</div>
            <div class="metric-value">{value}</div>
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

    # Q10 appears only here, as requested.
    if "Q10" in cleaned_data.columns:
        st.subheader("Q10: Nearest Cross Street")
        st.caption("Q10 is included only in the overview tab for planning reference.")
        q10_summary = summarize_single(cleaned_data["Q10"])
        st.dataframe(q10_summary, use_container_width=True)

# -----------------------------
# Question-by-question analysis
# -----------------------------
elif page == "Question Analysis":

    st.subheader("Question-by-Question Analysis")

    # Remove Q1 and Q10 from question-based analysis.
    question_options = [
        q for q in question_lookup["question_id"]
        if q in cleaned_data.columns and q not in ["Q1", "Q10"]
    ]

    selected_q = st.selectbox(
        "Select a question",
        question_options,
        format_func=lambda q: f"{q}: {question_dict[q]}"
    )

    st.subheader(question_dict[selected_q])

    # Q3, Q4, Q20 as ranges.
    if selected_q == "Q3":
        summary = summarize_range(cleaned_data[selected_q], commute_time_range)
        title = "Commute Time Ranges"

    elif selected_q == "Q4":
        summary = summarize_range(cleaned_data[selected_q], commute_distance_range)
        title = "Commute Distance Ranges"

    elif selected_q == "Q20":
        summary = summarize_range(cleaned_data[selected_q], commute_cost_range)
        title = "Daily Commute Cost Ranges"

    # Q6, Q9, Q14 as select-all-that-apply counts.
    elif selected_q in ["Q6", "Q9", "Q14"]:
        summary = summarize_multi(cleaned_data[selected_q], len(cleaned_data))
        title = "Selected Options Count"
        summary = summary.rename(columns={"Percent of Respondents": "Percent"})

    else:
        summary = summarize_single(cleaned_data[selected_q])
        title = "Response Distribution"

    if summary.empty:
        st.warning("No responses available for this question.")
        st.stop()

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("#### Response Summary")
        st.dataframe(summary, use_container_width=True)

    with col2:
        fig = plot_horizontal_bar(
            summary,
            y_col="Response",
            percent_col="Percent",
            title=title
        )
        st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# Open-ended themes
# -----------------------------
elif page == "Open-Ended Themes":

    st.subheader("Open-Ended Response Themes and Word Map")

    open_ended_questions = [
        q for q in ["Q18", "Q24", "Q25"]
        if q in cleaned_data.columns
    ]

    if not open_ended_questions:
        st.warning("Q18, Q24, or Q25 were not found in the dataset.")
        st.stop()

    selected_open_q = st.selectbox(
        "Select an open-ended question",
        open_ended_questions,
        format_func=lambda q: f"{q}: {question_dict[q]}"
    )

    st.markdown(f"### {selected_open_q}: {question_dict[selected_open_q]}")

    theme_summary, response_theme_df = create_theme_outputs(cleaned_data, selected_open_q)

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("#### Theme Counts")
        st.dataframe(theme_summary, use_container_width=True)

    with col2:
        if not theme_summary.empty:
            fig = px.bar(
                theme_summary.sort_values("Count"),
                x="Count",
                y="Theme",
                orientation="h",
                text="Percent",
                color="Theme",
                color_discrete_sequence=COLOR_SEQUENCE,
                title="Main Themes"
            )
            fig.update_traces(texttemplate="%{text}%")
            fig.update_layout(height=450, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No themes found for this question.")

    st.markdown("#### Word Map")
    st.caption("Words appear larger when they are repeated more often.")
    show_word_map(cleaned_data[selected_open_q])

    st.markdown("#### Open-Ended Responses")

    if not response_theme_df.empty:
        selected_theme = st.selectbox(
            "Filter responses by theme",
            ["All"] + list(theme_summary["Theme"])
        )

        filtered_responses = response_theme_df.copy()

        if selected_theme != "All":
            filtered_responses = filtered_responses[
                filtered_responses["Theme"] == selected_theme
            ]

        search_term = st.text_input("Search within responses")

        if search_term:
            filtered_responses = filtered_responses[
                filtered_responses["Response"]
                .astype(str)
                .str.contains(search_term, case=False, na=False)
            ]

        st.dataframe(filtered_responses, use_container_width=True)
    else:
        st.info("No open-ended responses found.")

# -----------------------------
# Relationship Analysis
# -----------------------------
elif page == "Relationship Analysis":

    st.subheader("Relationship Between Survey Questions")

    st.markdown("""
    Use this section to compare how answers to one question relate to another.
    Q1 and Q10 are removed from this section. Q3, Q4, and Q20 are grouped into ranges.
    Q6, Q9, and Q14 are treated as select-all-that-apply questions.
    """)

    question_ids = [
        q for q in question_lookup["question_id"]
        if q in cleaned_data.columns and q not in ["Q1", "Q10"]
    ]

    col1, col2 = st.columns(2)

    with col1:
        q1 = st.selectbox(
            "First question",
            question_ids,
            format_func=lambda q: f"{q}: {question_dict[q]}"
        )

    with col2:
        q2 = st.selectbox(
            "Second question",
            question_ids,
            index=1 if len(question_ids) > 1 else 0,
            format_func=lambda q: f"{q}: {question_dict[q]}"
        )

    if q1 == q2:
        st.warning("Please select two different questions.")
    else:
        relationship_data = cleaned_data.copy()

        # Explode multi-select questions if they are part of the relationship.
        if q1 in ["Q6", "Q9", "Q14"]:
            relationship_data = explode_multiselect_for_relationship(relationship_data, q1)

        if q2 in ["Q6", "Q9", "Q14"]:
            relationship_data = explode_multiselect_for_relationship(relationship_data, q2)

        if relationship_data.empty:
            st.warning("Not enough data to create this relationship.")
            st.stop()

        temp = pd.DataFrame({
            "First Question": transformed_series_for_relationship(relationship_data, q1),
            "Second Question": transformed_series_for_relationship(relationship_data, q2)
        })

        temp = temp.dropna()
        temp = temp[
            (temp["First Question"].astype(str).str.strip() != "") &
            (temp["Second Question"].astype(str).str.strip() != "")
        ]

        relationship_table = pd.crosstab(
            temp["First Question"],
            temp["Second Question"]
        )

        st.markdown("#### Cross-Tabulation")
        st.dataframe(relationship_table, use_container_width=True)

        heatmap_data = relationship_table.reset_index().melt(
            id_vars="First Question",
            var_name="Second Question",
            value_name="Count"
        )

        fig = px.density_heatmap(
            heatmap_data,
            x="Second Question",
            y="First Question",
            z="Count",
            text_auto=True,
            title="Relationship Heatmap",
            color_continuous_scale="YlGnBu"
        )

        fig.update_layout(height=650)
        st.plotly_chart(fig, use_container_width=True)
