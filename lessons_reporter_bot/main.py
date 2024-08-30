import inspect
from collections import defaultdict
from contextlib import suppress
from email import message
from functools import partial
from typing import Any, Literal

import telebot
from pydantic import ValidationError
from sqlmodel import SQLModel, create_engine
from telebot.apihelper import ApiTelegramException
from telebot.types import CallbackQuery, InlineKeyboardMarkup, Message
from telebot.util import quick_markup

from lessons_reporter_bot.authorization_service import AuthorizationService
from lessons_reporter_bot.bot_service import FORMATTED_HOMEWORK_STATUS_MAP, BotService
from lessons_reporter_bot.callback_data import (
    # Topic's callback's
    AddParentIdToStudentCallbackData,
    # Student's callback's
    CreateStudentCallbackData,
    CreateTopicCallbackData,
    DeleteConfirmedItemCallbackData,
    DeleteOneItemCallbackData,
    # Back to calback's
    GoBackToAdminPanelCallbackData,
    ReportBuilder1CallbackData,
    ReportBuilder1EnterManuallyCallbackData,
    ReportBuilder1SetValueFromButtonCallbackData,
    ReportBuilder5SetHomeworkStatusCallbackData,
    ReportBuilder6SetIsProactiveCallbackData,
    ReportBuilder7SetIsPaidCallbackData,
    ReportBuilder8AddCommentQuestionCallbackData,
    ReportBuilderChooseItemListCallbackData,
    # Report builder's callback's
    ReportBuilderShowItemListCallbackData,
    ReportBuilderShowReportPreviewCallbackData,
    SaveConfirmedReportCallbackData,
    SendSavedReportsCallbackData,
    ShowItemsListCallbackData,
    ShowOneItemCallbackData,
    UpdateStudentNameCallbackData,
    any_callback_data_validator,
)
from lessons_reporter_bot.callback_storage import CallbackStorage
from lessons_reporter_bot.models import (
    BotServiceMessage,
    BotServiceRegisterNextMessageHandler,
    FormattedPaginationItem,
    HomeworkStatus,
    Report,
    ReportData,
    Student,
    Topic,
)
from lessons_reporter_bot.report_builder import ReportBuilder
from lessons_reporter_bot.report_storage import ReportStorage
from lessons_reporter_bot.settings import Settings
from lessons_reporter_bot.student_storage import StudentStorage
from lessons_reporter_bot.topic_storage import TopicStorage
from lessons_reporter_bot.utils import FIRST_PAGE, paginate

settings = Settings()

engine = create_engine(settings.database_url)

topic_storage = TopicStorage(engine=engine)
report_builder = ReportBuilder()
student_storage = StudentStorage(engine=engine)
report_storage = ReportStorage(engine=engine)
authorization_service = AuthorizationService(superusers=settings.superusers)
bot_service = BotService(
    topic_storage=topic_storage,
    report_builder=report_builder,
    student_storage=student_storage,
    report_storage=report_storage,
    authorization_service=authorization_service,
)

telegram_bot = telebot.TeleBot(token=settings.bot_token)
callbacks = CallbackStorage(callbacks_version='1')


def _convert_button_dict(
    buttons: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    if callback_data := buttons.get('callback_data'):
        assert isinstance(callback_data, partial)
        buttons['callback_data'] = callbacks.to_callback_data(callback_data)
    return buttons


def build_quick_markup(
    buttons: dict[str, partial], row_width: int = 2
) -> InlineKeyboardMarkup:
    return quick_markup(
        values={name: _convert_button_dict(value) for (name, value) in buttons.items()},
        row_width=row_width,
    )


def build_menu_buttons() -> InlineKeyboardMarkup:
    return build_quick_markup(
        {
            'Студенты': {'callback_data': partial(show_student_list, 1)},
            # 'Темы уроков': {'callback_data': ''},
            'Отчёты': {'callback_data': partial(show_report_list, 1, 0)},
            # 'Составить отчёт': {'callback_data': ''},
        }
    )


@telegram_bot.message_handler(['start', 'help'])
def welcome(message: Message) -> None:
    if authorization_service.has_teacher_access(message.from_user.id):
        telegram_bot.send_message(
            message.chat.id, text=f'Главное меню:', reply_markup=build_menu_buttons()
        )
    else:
        telegram_bot.send_message(
            message.chat.id,
            text=f'Здравствуйте! Перешлите это сообщение Елене Петровне:\n`{message.from_user.id}`',
        )
        telegram_bot.send_message(
            message.chat.id,
            text='После этого бот будет присылать вам отчёты о проведённых занятиях. Если возникли вопросы, обратитесь к Елене Петровне. Спасибо!',
        )


@telegram_bot.callback_query_handler(lambda call: call)
def catchall_callback_handler(call: CallbackQuery) -> None:
    callback_partial = callbacks.from_callback_data(call.data)

    args = inspect.getfullargspec(callback_partial.func).args
    if 'call' in args:
        callback_partial.keywords['call'] = call
    if 'chat_id' in args:
        callback_partial.keywords['chat_id'] = call.from_user.id
    if 'message_id' in args:
        callback_partial.keywords['message_id'] = call.message.id

    print(callback_partial)
    callback_partial()


@callbacks.register
def show_menu(call: CallbackQuery) -> BotServiceMessage:
    telegram_bot.edit_message_text(
        chat_id=call.from_user.id,
        message_id=call.message.id,
        text=f'Главное меню:',
        reply_markup=build_menu_buttons(),
    )


@callbacks.register
def show_student_list(current_page: int, call: CallbackQuery) -> None:
    students = student_storage.list_students(order_by='name')
    pagination_result = paginate(
        items=students, current_page=current_page, page_size=10
    )
    buttons = {}

    for student in pagination_result.items:
        buttons[student.name] = {
            'callback_data': partial(show_one_student, student.student_id, current_page)
        }

    if not pagination_result.is_first_page:
        buttons['Назад'] = {
            'callback_data': partial(show_student_list, current_page - 1)
        }

    if not pagination_result.is_last_page:
        buttons['Вперёд'] = {
            'callback_data': partial(show_student_list, current_page + 1)
        }

    buttons['Добавить студента'] = {
        'callback_data': partial(create_student, current_page)
    }
    buttons['В меню'] = {'callback_data': partial(show_menu)}

    telegram_bot.edit_message_text(
        text='Выберите студента:',
        chat_id=call.from_user.id,
        message_id=call.message.id,
        reply_markup=build_quick_markup(buttons),
    )


@callbacks.register
def show_report_list(
    current_page: int, student_id: int | None, chat_id: int, message_id: int
) -> None:
    if student_id:
        reports = report_storage.list_reports_by_student_id(
            student_id=student_id, order_by='lesson_date', descending=True
        )
    else:
        reports = report_storage.list_reports(order_by='lesson_date', descending=True)

    pagination_result = paginate(items=reports, current_page=current_page, page_size=10)
    buttons = {}

    for report in pagination_result.items:
        if not (student := student_storage.get_student_by_id(report.student_id)):
            continue
        buttons[f'{report.lesson_date.strftime('%d-%m-%Y')} — {student.name}'] = {
            'callback_data': partial(show_one_report, report.report_id, current_page)
        }

    if not pagination_result.is_first_page:
        buttons['Назад'] = {
            'callback_data': partial(show_report_list, current_page - 1)
        }

    if not pagination_result.is_last_page:
        buttons['Вперёд'] = {
            'callback_data': partial(show_report_list, current_page + 1)
        }

    if student_id:
        buttons['Отправить сохранённые отчёты'] = {
            'callback_data': partial(send_saved_reports)
        }
    else:
        buttons['К студентам'] = {'callback_data': partial(show_student_list, 1)}

    buttons['В меню'] = {'callback_data': partial(show_menu)}

    telegram_bot.edit_message_text(
        text='Выберите отчёт:',
        chat_id=chat_id,
        message_id=message_id,
        reply_markup=build_quick_markup(buttons, row_width=1),
    )


@callbacks.register
def create_student(current_page: int, call: CallbackQuery) -> None:
    def process_student_name_input(message: Message) -> list[BotServiceMessage]:
        student_name = ' '.join(
            map(lambda word: word.capitalize(), message.text.strip().split())
        )
        student_id = student_storage.add_student(student_name)
        new_message = telegram_bot.send_message(call.from_user.id, '...')
        show_one_student(
            item_id=student_id,
            current_page=current_page,
            chat_id=new_message.chat.id,
            message_id=new_message.id,
        )

    telegram_bot.edit_message_text(
        text='Введите ФИО студента:',
        chat_id=call.from_user.id,
        message_id=call.message.id,
        reply_markup=None,
    )
    telegram_bot.register_next_step_handler_by_chat_id(
        call.from_user.id, process_student_name_input
    )


@callbacks.register
def show_one_student(
    item_id: int, current_page: int, chat_id: int, message_id: int
) -> None:
    if student := student_storage.get_student_by_id(item_id):
        text = f'ФИО: {student.name}\nРодитель id: {student.parent_id if student.parent_id else 'отсутсвует'}'
    else:
        text = 'Студент не найден'

    telegram_bot.edit_message_text(
        text=text,
        chat_id=chat_id,
        message_id=message_id,
        reply_markup=build_quick_markup(
            {
                # 'Отчёты': {'callback_data': partial(show_report_list, item_id)},
                # 'Удалить': {
                #     'callback_data': partial(delete_student, item_id, current_page)
                # },
                # 'Изменить ФИО': {
                #     'callback_data': partial(update_student_name, item_id, current_page)
                # },
                # 'Изменить id родителя': {
                #     'callback_data': partial(update_parent_id, item_id, current_page)
                # },
                'Назад': {'callback_data': partial(show_student_list, current_page)},
            }
        ),
    )


def format_report_text(
    report: Report | ReportData, student: Student, topic: Topic
) -> str:
    text = '\n'.join(
        (
            f'ФИО: {student.name}',
            f'Занятие № {report.lesson_count} от {report.lesson_date.strftime('%d-%m-%Y')}',
            f'Тема: {topic.topic}',
            f'Д/З: {FORMATTED_HOMEWORK_STATUS_MAP[report.homework_status]}',
            f'Активность на занятии {"высокая" if report.is_proactive else "слабая"}',
            f'Занятие {"оплачено" if report.is_paid else "не оплачено"}',
        )
    )
    if report.comment is not None:
        text += f'\nКомментарий:\n{report.comment}'

    return text


@callbacks.register
def show_one_report(item_id: int, current_page: int, call: CallbackQuery) -> None:
    if report := report_storage.get_report_by_id(item_id):
        if student := student_storage.get_student_by_id(report.student_id):
            if topic := topic_storage.get_topic_by_id(report.topic_id):
                text = format_report_text(report=report, student=student, topic=topic)
            else:
                text = 'Тема не найдена.'
        else:
            text = 'Студент не найден.'
    else:
        text = 'Отчёт не найден.'

    telegram_bot.edit_message_text(
        text=text,
        chat_id=call.from_user.id,
        message_id=call.message.id,
        reply_markup=None,
    )
    show_report_list(
        current_page=current_page,
        student_id=None,
        chat_id=call.from_user.id,
        message_id=call.message.id,
    )


if __name__ == '__main__':
    SQLModel.metadata.create_all(engine)
    print('Started bot')
    telegram_bot.polling(non_stop=True, interval=0.5)
