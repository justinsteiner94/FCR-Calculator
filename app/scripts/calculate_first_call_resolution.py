from typing import Any, List, Optional, Tuple

from dateutil.parser import parse as parse_date

from scripts.utils import open_workbook


def format_row(headers, row, report_date_column, is_reopened) -> dict[str, Any]:
    return {
        "datetime": row[headers.index(report_date_column)].value,
        "case_number": row[headers.index("Case Number")].value,
        "case_owner": row[headers.index("Case Owner")].value,
        "status": row[headers.index("Status")].value,
        "is_open": bool(int(row[headers.index("Open")].value)),
        "is_closed": bool(int(row[headers.index("Closed")].value)),
        "was_escalated": bool(int(row[headers.index("Was Escalated")].value)),
        "is_reopened": is_reopened,
    }


def get_cases(
    report_date, report_file, report_date_column, is_reopened, file_display_name
) -> List[dict[str, Any]]:

    wb = open_workbook(report_file, file_display_name)
    ws = wb.active

    try:
        cases = []
        for i, row in enumerate(ws.rows):
            if not i:
                headers = [c.value for c in row]
                report_date_index = headers.index(report_date_column)
                continue

            timestamp_cell = row[report_date_index]
            if isinstance(timestamp_cell.value, str):
                timestamp_cell.value = parse_date(timestamp_cell.value)

            if timestamp_cell.value.date() != report_date:
                continue

            cases.append(format_row(headers, row, report_date_column, is_reopened))

        return cases

    except ValueError as e:
        raise ValueError(
            f"Unable to parse columns for {file_display_name} file; is it in the right format?"
        ) from e


def keep_unique_case_by_newest_datetime(
    cases: List[dict[str, Any]]
) -> List[dict[str, Any]]:
    # sort by case number asc, datetime desc
    cases.sort(key=lambda x: x["datetime"], reverse=True)
    cases.sort(key=lambda x: x["case_number"])

    # remove duplicates
    case_numbers = set()
    unique_cases: List[dict[str, Any]] = []
    for case in cases:
        if case["case_number"] not in case_numbers:
            case_numbers.add(case["case_number"])
            unique_cases.append(case)

    return unique_cases


def get_child_case_count(report_file, child_case_threshold, whitespace_offset=1) -> int:
    wb = open_workbook(report_file, file_display_name="Parent Cases Report")
    ws = wb.active
    child_case_count: int = 0

    # find the "Subtotal" rows and sum them if they exceed the threshold
    for row in ws.rows:
        if row[whitespace_offset].value == "Subtotal":
            case_count = row[whitespace_offset + 2].value
            if case_count >= child_case_threshold:
                child_case_count += case_count

    return child_case_count


def get_closed_and_escalated_cases(
    cases: List[dict[str, Any]]
) -> Tuple[List[dict[str, Any]], List[dict[str, Any]]]:
    # filter to only cases that are not re-opened
    closed_cases = [case for case in cases if not case["is_reopened"]]
    escalated_cases = [case for case in closed_cases if case["was_escalated"]]

    return closed_cases, escalated_cases


def main(
    report_date,
    fcr_reopened_file,
    fcr_closed_file,
    fcr_parent_file,
    child_case_threshold: int,
    child_case_count_override: Optional[int] = None,
) -> dict[str, int]:

    cases = get_cases(
        report_date,
        fcr_reopened_file,
        "Edit Date",
        is_reopened=True,
        file_display_name="Re-opened Report",
    )

    cases.extend(
        get_cases(
            report_date,
            fcr_closed_file,
            "Date/Time Opened",
            is_reopened=False,
            file_display_name="Closed Report",
        )
    )

    cases = keep_unique_case_by_newest_datetime(cases)

    if not cases:
        raise ValueError("No cases found for the given report date")

    child_case_count = (
        child_case_count_override
        if child_case_count_override is not None
        else get_child_case_count(
            fcr_parent_file,
            child_case_threshold,
        )
    )

    closed_cases, escalated_cases = get_closed_and_escalated_cases(cases)

    return {
        "closed_case_count": len(closed_cases),
        "escalated_case_count": len(escalated_cases),
        "child_case_count": child_case_count,
        "total_cases": len(cases),
    }
