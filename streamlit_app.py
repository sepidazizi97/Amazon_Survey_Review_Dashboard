import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Amazon Transportation Survey Dashboard",
    layout="wide"
)

st.title("Amazon Transportation Survey Dashboard")
st.write("Ben Franklin Transit | Employee Transportation Survey Analysis")

uploaded_file = st.file_uploader(
    "Upload the cleaned Excel file",
    type=["xlsx"]
)

if uploaded_file is not None:

    xls = pd.ExcelFile(uploaded_file)

    cleaned_data = pd.read_excel(uploaded_file, sheet_name="cleaned_data")
    question_lookup = pd.read_excel(uploaded_file, sheet_name="question_lookup")

    st.sidebar.header("Dashboard Navigation")
    page = st.sidebar.radio(
        "Select a section",
        [
            "Overview",
            "Question-by-Question Analysis",
            "Open-Ended Themes",
            "Open-Ended Responses",
            "Relational Analysis"
        ]
    )

    # -----------------------------
    # Overview
    # -----------------------------
    if page == "Overview":
        st.header("Survey Overview")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Total Responses", len(cleaned_data))

        with col2:
            st.metric("Total Questions", len(question_lookup))

        with col3:
            st.metric("Available Sheets", len(xls.sheet_names))

        st.subheader("Cleaned Data Preview")
        st.dataframe(cleaned_data.head(20), use_container_width=True)

        st.subheader("Question Lookup")
        st.dataframe(question_lookup, use_container_width=True)

    # -----------------------------
    # Question-by-question analysis
    # -----------------------------
    elif page == "Question-by-Question Analysis":
        st.header("Question-by-Question Analysis")

        question_options = dict(
            zip(question_lookup["question_id"], question_lookup["question_text"])
        )

        selected_q = st.selectbox(
            "Select a question",
            list(question_options.keys()),
            format_func=lambda x: f"{x}: {question_options[x]}"
        )

        st.subheader(question_options[selected_q])

        if selected_q in cleaned_data.columns:
            q_data = cleaned_data[selected_q].dropna().astype(str)

            summary = (
                q_data.value_counts()
                .reset_index()
            )
            summary.columns = ["Response", "Count"]
            summary["Percent"] = round(summary["Count"] / summary["Count"].sum() * 100, 2)

            st.dataframe(summary, use_container_width=True)

            fig = px.bar(
                summary,
                x="Response",
                y="Count",
                text="Percent",
                title=f"Response Distribution for {selected_q}"
            )

            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

    # -----------------------------
    # Open-ended themes
    # -----------------------------
    elif page == "Open-Ended Themes":
        st.header("Open-Ended Theme Analysis")

        if "theme_summary" in xls.sheet_names:
            theme_summary = pd.read_excel(uploaded_file, sheet_name="theme_summary")

            st.dataframe(theme_summary, use_container_width=True)

            selected_theme_q = st.selectbox(
                "Select an open-ended question",
                theme_summary["question_id"].unique()
            )

            filtered_theme = theme_summary[
                theme_summary["question_id"] == selected_theme_q
            ]

            fig = px.bar(
                filtered_theme,
                x="theme",
                y="count",
                title=f"Top Themes for {selected_theme_q}",
                text="count"
            )

            st.plotly_chart(fig, use_container_width=True)

        else:
            st.warning("No theme_summary sheet found.")

    # -----------------------------
    # Open-ended responses
    # -----------------------------
    elif page == "Open-Ended Responses":
        st.header("Open-Ended Responses with Themes")

        if "open_ended_themes" in xls.sheet_names:
            open_responses = pd.read_excel(uploaded_file, sheet_name="open_ended_themes")

            selected_open_q = st.selectbox(
                "Select an open-ended question",
                open_responses["question_id"].unique()
            )

            filtered_responses = open_responses[
                open_responses["question_id"] == selected_open_q
            ]

            st.dataframe(filtered_responses, use_container_width=True)

            search_term = st.text_input("Search responses")

            if search_term:
                searched = filtered_responses[
                    filtered_responses["response_text"]
                    .astype(str)
                    .str.contains(search_term, case=False, na=False)
                ]

                st.write(f"Search results for: {search_term}")
                st.dataframe(searched, use_container_width=True)

        else:
            st.warning("No open_ended_themes sheet found.")

    # -----------------------------
    # Relational analysis
    # -----------------------------
    elif page == "Relational Analysis":
        st.header("Relational Analysis")

        relational_sheets = [
            sheet for sheet in xls.sheet_names
            if "_by_" in sheet
        ]

        if relational_sheets:
            selected_sheet = st.selectbox(
                "Select a relationship table",
                relational_sheets
            )

            relationship_data = pd.read_excel(
                uploaded_file,
                sheet_name=selected_sheet
            )

            st.subheader(selected_sheet)
            st.dataframe(relationship_data, use_container_width=True)

        else:
            st.warning("No relational analysis sheets found.")

else:
    st.info("Please upload your cleaned Excel file to begin.")
