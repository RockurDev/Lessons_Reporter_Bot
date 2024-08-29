from typing import Optional

from sqlmodel import Session, create_engine, desc, func, select

from lessons_reporter_bot.models import Report, ReportData


class ReportStorage:
    def __init__(self, engine: create_engine) -> None:
        self.engine = engine

    def count_reports(self) -> int:
        with Session(self.engine) as session:
            statement = select(Report)
            result = session.exec(statement)
            return len(result.all())

    def add_report(self, report: ReportData) -> None:
        with Session(self.engine) as session:
            session.add(report)
            session.commit()

    def list_reports(
        self, order_by: str | None = None, descending: bool = False
    ) -> list[Report]:
        with Session(self.engine) as session:
            statement = select(Report)
            if order_by:
                column = getattr(Report, order_by)
                statement = (
                    statement.order_by(desc(column))
                    if descending
                    else statement.order_by(column)
                )
            return session.exec(statement).all()

    def list_reports_by_student_id(
        self, student_id: int, order_by: str | None = None, descending: bool = False
    ) -> list[Report]:
        with Session(self.engine) as session:
            statement = select(Report).where(Report.student_id == student_id)
            if order_by:
                column = getattr(Report, order_by)
                statement = (
                    statement.order_by(desc(column))
                    if descending
                    else statement.order_by(column)
                )
            return session.exec(statement).all()

    def get_report_by_id(self, report_id: int) -> Optional[Report]:
        with Session(self.engine) as session:
            statement = select(Report).where(Report.report_id == report_id)
            return session.exec(statement).first()

    def lessons_count_by_student_id(self, student_id: int) -> int:
        with Session(self.engine) as session:
            statement = select(func.count(Report.report_id)).where(
                Report.student_id == student_id
            )
            return session.exec(statement).first()

    def get_saved_reports(self) -> list:
        with Session(self.engine) as session:
            statement = select(Report).where(Report.is_sent == False)
            return session.exec(statement).all()

    def set_is_sent(self, report_id: int) -> None:
        with Session(self.engine) as session:
            report = session.get(Report, report_id)
            report.is_sent = True
            session.commit()
