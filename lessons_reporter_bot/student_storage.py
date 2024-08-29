from typing import List, Optional

from sqlmodel import Session, desc, select

from lessons_reporter_bot.models import Student


class StudentStorage:
    def __init__(self, engine) -> None:
        self.engine = engine

    def count_students(self) -> int:
        with Session(self.engine) as session:
            return session.exec(select(Student)).count()

    def add_student(self, student_name: str) -> int:
        new_student = Student(name=student_name)
        with Session(self.engine) as session:
            session.add(new_student)
            session.commit()
            session.refresh(new_student)
        return new_student.student_id

    def add_parent_id_to_student(self, student_id: int, parent_id: int) -> None:
        with Session(self.engine) as session:
            student = session.exec(
                select(Student).where(Student.student_id == student_id)
            ).first()
            if student:
                student.parent_id = parent_id
                session.commit()

    def get_student_by_id(self, student_id: int) -> Optional[Student]:
        with Session(self.engine) as session:
            return session.exec(
                select(Student).where(Student.student_id == student_id)
            ).first()

    def get_parent_id(self, student_id: int) -> int:
        with Session(self.engine) as session:
            student = session.exec(
                select(Student).where(Student.student_id == student_id)
            ).first()
            return student.parent_id if student else None

    def list_students(
        self, order_by: str | None = None, descending: bool = False
    ) -> List[Student]:
        with Session(self.engine) as session:
            statement = select(Student)
            if order_by:
                column = getattr(Student, order_by)
                statement = (
                    statement.order_by(desc(column))
                    if descending
                    else statement.order_by(column)
                )
            return session.exec(statement).all()

    def update_student_name(self, student_id: int, student_name: str) -> None:
        with Session(self.engine) as session:
            student = session.exec(
                select(Student).where(Student.student_id == student_id)
            ).first()
            if student:
                student.name = student_name
                session.commit()

    def delete_student(self, student_id: int) -> bool:
        with Session(self.engine) as session:
            student = session.exec(
                select(Student).where(Student.student_id == student_id)
            ).first()
            if student:
                session.delete(student)
                session.commit()
                return True
            return False
