from dataclasses import dataclass, field
from datetime import date

import pydantic

from lessons_reporter_bot.models import ReportData


class TempReport(pydantic.BaseModel):
    lesson_date: date | None = None
    lesson_count: int | None = None
    topic_id: int | None = None
    student_id: int | None = None
    homework_status: int | None = None
    is_proactive: bool | None = None
    is_paid: bool | None = None
    comment: str | None = None


@dataclass
class ReportBuilder:
    temp_report: TempReport = field(default_factory=TempReport)

    def clear_temp_report(self) -> None:
        self.temp_report = TempReport()

    def set_lesson_date_1(self, lesson_date: date) -> None:
        self.temp_report.lesson_date = lesson_date

    def set_lesson_count_4(self, lesson_count: int) -> None:
        self.temp_report.lesson_count = lesson_count

    def set_topic_id_(self, topic_id: int) -> None:
        self.temp_report.topic_id = topic_id

    def set_student_id_3(self, student_id: int) -> None:
        self.temp_report.student_id = student_id

    def set_homework_status_5(self, homework_status: int) -> None:
        self.temp_report.homework_status = homework_status

    def set_is_proactive_6(self, is_proactive: bool) -> None:
        self.temp_report.is_proactive = is_proactive

    def set_is_paid_7(self, is_paid: bool) -> None:
        self.temp_report.is_paid = is_paid

    def set_comment_8(self, text: str | None) -> None:
        self.temp_report.comment = text

    def preview_complete_report(self) -> ReportData:
        return ReportData.model_validate(self.temp_report, from_attributes=True)

    def complete_report(self) -> ReportData:
        report = self.preview_complete_report()
        self.clear_temp_report()
        return report
