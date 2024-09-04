import time
from collections import defaultdict
from contextlib import suppress

import telebot
from pydantic import ValidationError
from sqlmodel import SQLModel, create_engine
from telebot.apihelper import ApiTelegramException
from telebot.types import CallbackQuery, Message
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
from lessons_reporter_bot.models import (
    BotServiceMessage,
    BotServiceRegisterNextMessageHandler,
)
from lessons_reporter_bot.report_builder import ReportBuilder
from lessons_reporter_bot.report_storage import ReportStorage
from lessons_reporter_bot.settings import Settings
from lessons_reporter_bot.student_storage import StudentStorage
from lessons_reporter_bot.topic_storage import TopicStorage
from lessons_reporter_bot.utils import FIRST_PAGE

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

LAST_MESSAGE_IDS: dict[int, list[int]] = defaultdict(list)


def process_bot_service_handler_results(
    *results: BotServiceMessage | BotServiceRegisterNextMessageHandler, chat_id: int
) -> Message:
    sent_message = None

    for result in results:
        match result:
            case BotServiceMessage() as message:
                telegram_bot.clear_step_handler_by_chat_id(chat_id)

                if authorization_service.has_teacher_access(user_id=chat_id):
                    for message_id in LAST_MESSAGE_IDS[chat_id]:
                        # Ignore if the message is already deleted or not found
                        with suppress(ApiTelegramException):
                            telegram_bot.delete_message(chat_id, message_id)

                buttons = {
                    button.title: {
                        'callback_data': button.callback_data.model_dump_json()
                    }
                    for button in message.buttons
                }
                reply_markup = (
                    quick_markup(buttons, row_width=message.row_width)
                    if message.buttons
                    else None
                )

                sent_message = telegram_bot.send_message(
                    chat_id,
                    message.text,
                    reply_markup=reply_markup,
                    parse_mode='MARKDOWN',
                )

                if authorization_service.has_teacher_access(user_id=chat_id):
                    LAST_MESSAGE_IDS[chat_id].append(sent_message.message_id)

            case BotServiceRegisterNextMessageHandler():
                def callback(message: Message) -> None:
                    process_bot_service_handler_results(
                        *result.callback(message.text), chat_id=chat_id
                    )

                telegram_bot.register_next_step_handler_by_chat_id(
                    chat_id=chat_id, callback=callback
                )

    return sent_message


@telegram_bot.message_handler(['start', 'help'])
def welcome(message: Message) -> None:
    user_id = message.from_user.id
    process_bot_service_handler_results(*bot_service.welcome(user_id), chat_id=user_id)


@telegram_bot.callback_query_handler(lambda call: call)
def catchall_callback_handler(call: CallbackQuery) -> None:
    user_id = call.from_user.id
    match data := any_callback_data_validator.validate_json(call.data):
        case GoBackToAdminPanelCallbackData():
            process_bot_service_handler_results(
                *bot_service.welcome(user_id), chat_id=user_id
            )

        case CreateTopicCallbackData():
            process_bot_service_handler_results(
                *bot_service.create_topic(data), chat_id=user_id
            )

        case CreateStudentCallbackData():
            process_bot_service_handler_results(
                *bot_service.create_student(data), chat_id=user_id
            )

        case AddParentIdToStudentCallbackData():
            process_bot_service_handler_results(
                *bot_service.add_parent_id_to_student(data, student_id=data.student_id),
                chat_id=user_id,
            )

        case UpdateStudentNameCallbackData():
            process_bot_service_handler_results(
                *bot_service.update_student_name(data), chat_id=user_id
            )

        case ReportBuilder1CallbackData():
            report_builder.clear_temp_report()
            process_bot_service_handler_results(
                bot_service.build_report_1_lesson_date_setting(), chat_id=user_id
            )

        case ReportBuilder1SetValueFromButtonCallbackData():
            process_bot_service_handler_results(
                *bot_service.build_report_1_lesson_date_from_button(
                    lesson_day=data.lesson_day
                ),
                chat_id=user_id,
            )

        case ReportBuilder1EnterManuallyCallbackData():
            process_bot_service_handler_results(
                *bot_service.build_report_1_manual(), chat_id=user_id
            )

        case ReportBuilderShowItemListCallbackData():
            if data.i_t == 'T':
                process_bot_service_handler_results(
                    bot_service.build_report_2_topic_setting(
                        data=ReportBuilderShowItemListCallbackData(
                            i_t='T', page=data.page
                        ),
                    ),
                    chat_id=user_id,
                )
            elif data.i_t == 'S':
                process_bot_service_handler_results(
                    bot_service.build_report_3_student_setting(
                        data=ReportBuilderShowItemListCallbackData(
                            i_t='S', page=data.page
                        ),
                    ),
                    chat_id=user_id,
                )

        case ReportBuilderChooseItemListCallbackData():
            if data.i_t == 'T':
                report_builder.set_topic_id_(topic_id=data.i_id)
                process_bot_service_handler_results(
                    bot_service.build_report_3_student_setting(
                        data=ReportBuilderShowItemListCallbackData(
                            i_t='S', page=FIRST_PAGE
                        ),
                    ),
                    chat_id=user_id,
                )
            elif data.i_t == 'S':
                report_builder.set_student_id_3(student_id=data.i_id)
                report_builder.set_lesson_count_4(
                    report_storage.lessons_count_by_student_id(student_id=data.i_id) + 1
                )
                process_bot_service_handler_results(
                    bot_service.build_report_5_homework_status_setting(),
                    chat_id=user_id,
                )

        case ReportBuilder5SetHomeworkStatusCallbackData():
            report_builder.set_homework_status_5(data.homework_status)
            process_bot_service_handler_results(
                bot_service.build_report_6_is_proactive_setting(),
                chat_id=user_id,
            )

        case ReportBuilder6SetIsProactiveCallbackData():
            report_builder.set_is_proactive_6(bool(data.is_active))
            process_bot_service_handler_results(
                bot_service.build_report_7_payment_status_setting(),
                chat_id=user_id,
            )

        case ReportBuilder7SetIsPaidCallbackData():
            report_builder.set_is_paid_7(bool(data.payment_status))
            process_bot_service_handler_results(
                bot_service.build_report_8_ask_comment(),
                chat_id=user_id,
            )

        case ReportBuilder8AddCommentQuestionCallbackData():
            process_bot_service_handler_results(
                *bot_service.build_report_8_get_comment(),
                chat_id=user_id,
            )

        case ReportBuilderShowReportPreviewCallbackData():
            process_bot_service_handler_results(
                bot_service.build_report_preview(),
                chat_id=user_id,
            )

        case SaveConfirmedReportCallbackData():
            try:
                report_id, complete_report = bot_service.save_report()

                if data.parent_id:
                    sent_message = process_bot_service_handler_results(
                        bot_service.build_report_message(complete_report),
                        chat_id=data.parent_id,
                    )

                    if sent_message:
                        process_bot_service_handler_results(
                            bot_service.get_message_report_successfully_sent(),
                            chat_id=user_id,
                        )
                        report_storage.set_is_sent(report_id)
                    else:
                        process_bot_service_handler_results(
                            bot_service.get_message_report_unsuccessfully_sent(),
                            chat_id=user_id,
                        )

                    # # Introduce a delay to make the success message appear later
                    time.sleep(1.5)

            except ApiTelegramException as e:
                if e.error_code == 400 and 'chat not found' in e.description.lower():
                    process_bot_service_handler_results(
                        bot_service.get_message_report_unsuccessfully_sent(),
                        chat_id=user_id,
                    )

            except ValidationError:
                process_bot_service_handler_results(
                    bot_service.get_error_message_temp_report_must_be_filled()
                )

            process_bot_service_handler_results(
                *bot_service.welcome(user_id),
                chat_id=user_id,
            )

        case SendSavedReportsCallbackData():
            for sent_message, report_id, parent_id in bot_service.send_saved_reports():
                try:
                    process_bot_service_handler_results(sent_message, chat_id=parent_id)
                    report_storage.set_is_sent(report_id)
                except ApiTelegramException as e:
                    if (
                        e.error_code == 400
                        and 'chat not found' in e.description.lower()
                    ):
                        process_bot_service_handler_results(
                            'Пользователь (родитель) не найден. Проверьте id.',
                            chat_id=parent_id,
                        )

        case ShowItemsListCallbackData():
            process_bot_service_handler_results(
                bot_service.show_items_list(data), chat_id=user_id
            )

        case ShowOneItemCallbackData():
            process_bot_service_handler_results(
                bot_service.show_one_item(data), chat_id=user_id
            )

        case DeleteOneItemCallbackData():
            process_bot_service_handler_results(
                bot_service.delete_one_item(data), chat_id=user_id
            )

        case DeleteConfirmedItemCallbackData():
            process_bot_service_handler_results(
                bot_service.delete_confirmed_one_item(data),
                chat_id=user_id,
            )

        case other_callback_data:
            print('other_callback_data', other_callback_data)


if __name__ == '__main__':
    SQLModel.metadata.create_all(engine)
    print('Started bot')
    telegram_bot.polling(non_stop=True, interval=0.5)
