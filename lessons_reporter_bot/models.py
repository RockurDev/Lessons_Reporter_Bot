import enum
from dataclasses import dataclass, field
from datetime import date
from typing import Optional, Protocol, TypedDict

import pydantic
from sqlmodel import Field, Relationship, SQLModel

from lessons_reporter_bot.callback_data import AnyCallbackData


@dataclass
class BotServiceMessage:
    text: str
    buttons: list['BotServiceMessageButton'] = field(default_factory=list)
    row_width: int = 2


class NextMessageCallback(Protocol):
    def __call__(
        self, message_text: str
    ) -> list['BotServiceMessage | BotServiceRegisterNextMessageHandler']: ...


@dataclass
class BotServiceRegisterNextMessageHandler:
    callback: NextMessageCallback


class FormattedPaginationItem(TypedDict):
    title: str
    id: int


class Topic(SQLModel, table=True):
    topic_id: int = Field(default=None, primary_key=True)
    topic: str

    reports: list['Report'] = Relationship(back_populates='topic')


class Student(SQLModel, table=True):
    student_id: int = Field(default=None, primary_key=True)
    name: str
    parent_id: Optional[int] = Field(default=None)

    reports: list['Report'] = Relationship(back_populates='student')


class Report(SQLModel, table=True):
    report_id: int = Field(default=None, primary_key=True)
    lesson_date: date
    lesson_count: int
    topic_id: int = Field(foreign_key='topic.topic_id', nullable=True)
    student_id: int = Field(foreign_key='student.student_id', nullable=True)
    homework_status: int
    is_proactive: bool
    is_paid: bool
    is_sent: bool
    comment: str = Field(nullable=True)

    topic: Topic = Relationship(back_populates='reports')
    student: Student = Relationship(back_populates='reports')


class BotServiceMessageButton(pydantic.BaseModel):
    title: str
    callback_data: AnyCallbackData


class ReportData(pydantic.BaseModel):
    lesson_date: date
    lesson_count: int
    topic_id: int
    student_id: int
    homework_status: int
    is_proactive: bool
    is_paid: bool
    comment: str | None
