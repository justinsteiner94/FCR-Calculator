from datetime import date, datetime, time, timedelta
from typing import cast

import streamlit as st
from scripts.build_case_report import main as build_case_report
from scripts.calculate_first_call_resolution import (
    main as calculate_first_call_resolution,
)
from scripts.utils import format_percent

st.title("Reporting Tools")

fcr_tab, case_report_tab = st.tabs(
    ["First Call Resolution Calculator", "Case Report Formatter"]
)

with fcr_tab:
    st.header("First Call Resolution Calculator")
    calculations: dict[str, int] = {}

    with st.form("fcr_calculator"):
        fcr_reopened_file = st.file_uploader(
            "1. FCR Re-opened Report", type=["xlsx", "xls"]
        )
        fcr_closed_file = st.file_uploader("2. FCR Closed Report", type=["xlsx", "xls"])
        fcr_parent_file = st.file_uploader(
            "3. FCR Parent Cases Report", type=["xlsx", "xls"]
        )

        st.markdown("---")

        report_date = st.date_input(
            "Report Date", value=datetime.today() - timedelta(days=15)
        )
        child_case_threshold = int(
            st.number_input("Child Case Threshold", value=4, min_value=0)
        )
        fcr_submitted = st.form_submit_button("Calculate First Call Resolution")

        if fcr_submitted:
            if not all([fcr_reopened_file, fcr_closed_file, fcr_parent_file]):
                st.markdown(
                    '<span style="color:red">**All three files are required**</span>',
                    unsafe_allow_html=True,
                )

            else:
                try:
                    calculations = calculate_first_call_resolution(
                        report_date,
                        fcr_reopened_file,
                        fcr_closed_file,
                        fcr_parent_file,
                        child_case_threshold,
                    )

                except ValueError as e:
                    st.markdown(
                        f'<span style="color:red">**Error: _{e}_**</span>',
                        unsafe_allow_html=True,
                    )

    if calculations:
        fcr = (
            calculations["closed_case_count"]
            - calculations["escalated_case_count"]
            - calculations["child_case_count"]
        ) / calculations["total_cases"]

        _, fcr_column, _ = st.columns(3)
        fcr_column.metric("First Call Resolution", format_percent(fcr))

        with st.expander("See calculated data"):
            st.latex(
                r"""\frac{closed\ cases - escalated\ cases - child\ cases}{total\ cases}"""
            )

            # we tell streamlit that these values are ints to avoid decimal points, despite their types always being ints
            subcol1, subcol2, subcol3, subcol4 = st.columns(4)
            subcol1.metric("Closed Case Count", int(calculations["closed_case_count"]))
            subcol2.metric(
                "Escalated Case Count", int(calculations["escalated_case_count"])
            )
            subcol3.metric("Child Case Count", int(calculations["child_case_count"]))
            subcol4.metric("Total Cases", int(calculations["total_cases"]))

with case_report_tab:
    st.header("Case Report Formatter")
    new_report_filepath = ""

    with st.form("case_report"):
        case_report_file = st.file_uploader("Case Report File", type="xlsx")
        report_date = st.date_input("Report Date")
        report_time = st.time_input("Report Run Time", time(hour=13))
        report_datetime = datetime.combine(cast(date, report_date), report_time)

        with st.expander("Cycle Performance Thresholds"):
            st.markdown(
                """
                Values must be in ascending order. Ranges are _non-inclusive_  
                (e.g. a threshold of 1 means _less than_ 1)
                """
            )

            col1, col2 = st.columns(2)
            meets_color = col2.color_picker("Meets Color", value="#92D050", label_visibility="hidden")
            outstanding_val = col1.slider(
                "Meets", value=0.91, min_value=0.0, max_value=5.0, step=0.01
            )

            col1, col2 = st.columns(2)
            does_not_meet_color = col2.color_picker("Does Not Meet", value="#FF0000", label_visibility="hidden")

            # this isn't actually used since it's the final threshold, it's just here for display purposes
            col1.slider("Does Not Meet (default)", value=5.0, disabled=True)

        case_report_submitted = st.form_submit_button("Format Case Report")

        if case_report_submitted:
            if not case_report_file:
                st.markdown(
                    '<span style="color:red">**Please upload your Case Report file**</span>',
                    unsafe_allow_html=True,
                )

            else:
                try:
                    new_report_filepath = build_case_report(
                        case_report_file,
                        report_datetime,
                        outstanding_val,
                        outstanding_color,
                        exceeds_val,
                        exceeds_color,
                        competent_val,
                        competent_color,
                        needs_improvement_color,
                    )

                except ValueError as e:
                    st.markdown(
                        f'<span style="color:red">**Error: _{e}_**</span>',
                        unsafe_allow_html=True,
                    )

    if new_report_filepath:
        col1, col2, col3 = st.columns(3)
        with open(new_report_filepath, "rb") as f:
            col2.download_button(
                "Download your formatted Case Report",
                f,
                file_name=f"Workload Management Report {report_datetime.strftime('%-m-%-d-%Y')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
