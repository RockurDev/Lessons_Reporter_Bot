import inspect
from collections import defaultdict
from contextlib import suppress
from functools import partial
from typing import Any, Literal

import telebot
from pydantic import ValidationError
from sqlmodel import SQLModel, create_engine
from telebot.apihelper import ApiTelegramException
from telebot.types import CallbackQuery, InlineKeyboardMarkup, Message
from telebot.util import quick_markup

from lessons_reporter_bot.authorization_service import AuthorizationService
from lessons_reporter_bot.bot_service import BotService
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
        values={
            name: _convert_button_dict(value) for (name, value) in buttons.values()
        },
        row_width=row_width,
    )

    # return BotServiceMessage(
    #     text='Главное меню:',
    #     buttons=[
    #         BotServiceMessageButton(
    #             title='Студенты',
    #             callback_data=ShowItemsListCallbackData(i_t='S', i_f=None, page=1),
    #         ),
    #         BotServiceMessageButton(
    #             title='Темы уроков',
    #             callback_data=ShowItemsListCallbackData(i_t='T', i_f=None, page=1),
    #         ),
    #         BotServiceMessageButton(
    #             title='Отчёты',
    #             callback_data=ShowItemsListCallbackData(i_t='R', i_f=None, page=1),
    #         ),
    #         BotServiceMessageButton(
    #             title='Составить отчёт',
    #             callback_data=ReportBuilder1CallbackData(),
    #         ),
    #     ],
    # )


def build_menu_buttons() -> InlineKeyboardMarkup:
    return build_quick_markup(
        {
            'Студенты': {'callback_data': partial(show_student_list, 1)},
            'Темы уроков': {'callback_data': ''},
            'Отчёты': {'callback_data': ''},
            'Составить отчёт': {'callback_data': ''},
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

    callback_partial()


@callbacks.register
def show_one_student(item_id: int, current_page: int) -> None: ...


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
            'callback_data': partial(show_one_student, student.id, current_page)
        }

    if not pagination_result.is_first_page:
        buttons['Назад'] = {
            'callback_data': partial(show_student_list, current_page - 1)
        }

    if not pagination_result.is_last_page:
        buttons['Вперёд'] = {
            'callback_data': partial(show_student_list, current_page + 1)
        }

    # buttons['Добавить студента'] = {'callback_data': partial(create_student, current_page)}
    buttons['В меню'] = {'callback_data': partial(show_menu, current_page)}
    telegram_bot.edit_message_text(
        text='Выберите студента:',
        chat_id=call.from_user.id,
        message_id=call.message.id,
        reply_markup=build_quick_markup(buttons),
    )


if __name__ == '__main__':
    SQLModel.metadata.create_all(engine)
    print('Started bot')
    telegram_bot.polling(non_stop=True, interval=0.5)
