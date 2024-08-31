from dataclasses import dataclass
from datetime import datetime, timedelta

from lessons_reporter_bot.authorization_service import AuthorizationService
from lessons_reporter_bot.callback_data import (
    # Topic's callback's
    AddParentIdToStudentCallbackData,
    # Student's callback's
    CreateStudentCallbackData,
    CreateTopicCallbackData,
    DeleteConfirmedItemCallbackData,
    DeleteOneItemCallbackData,
    # Back to callback's
    GoBackToAdminPanelCallbackData,
    # Report builder's callback's
    ReportBuilder1CallbackData,
    ReportBuilder1EnterManuallyCallbackData,
    ReportBuilder1SetValueFromButtonCallbackData,
    ReportBuilder5SetHomeworkStatusCallbackData,
    ReportBuilder6SetIsProactiveCallbackData,
    ReportBuilder7SetIsPaidCallbackData,
    ReportBuilder8AddCommentQuestionCallbackData,
    ReportBuilderChooseItemListCallbackData,
    ReportBuilderShowItemListCallbackData,
    ReportBuilderShowReportPreviewCallbackData,
    SaveConfirmedReportCallbackData,
    SendSavedReportsCallbackData,
    ShowItemsListCallbackData,
    ShowOneItemCallbackData,
    UpdateStudentNameCallbackData,
)
from lessons_reporter_bot.models import (
    BotServiceMessage,
    BotServiceMessageButton,
    BotServiceRegisterNextMessageHandler,
    FormattedPaginationItem,
    Report,
    ReportData,
)
from lessons_reporter_bot.report_builder import ReportBuilder
from lessons_reporter_bot.report_storage import ReportStorage
from lessons_reporter_bot.settings import UserId
from lessons_reporter_bot.student_storage import StudentStorage
from lessons_reporter_bot.topic_storage import TopicStorage
from lessons_reporter_bot.utils import paginate

FORMATTED_HOMEWORK_STATUS_MAP = {
    2: 'выполнено',
    1: 'частично выполнено',
    0: 'не выполнено',
}


@dataclass
class BotService:
    authorization_service: AuthorizationService
    topic_storage: TopicStorage
    student_storage: StudentStorage
    report_builder: ReportBuilder
    report_storage: ReportStorage

    def welcome(self, user_id: UserId) -> list[BotServiceMessage]:
        if self.authorization_service.has_teacher_access(user_id):
            return [
                self.show_admin_panel(),
            ]
        return [
            BotServiceMessage(
                text=f'Здравствуйте! Перешлите это сообщение Елене Петровне:\n`{user_id}`',
                buttons=[],
            ),
            BotServiceMessage(
                text=(
                    'После этого бот будет присылать вам отчёты'
                    ' о проведённых занятиях. Если возникли вопросы,'
                    ' обратитесь к Елене Петровне. Спасибо!'
                ),
                buttons=[],
            ),
        ]

    def show_admin_panel(self) -> BotServiceMessage:
        return BotServiceMessage(
            text='Главное меню:',
            buttons=[
                BotServiceMessageButton(
                    title='Студенты',
                    callback_data=ShowItemsListCallbackData(i_t='S', i_f=None, page=1),
                ),
                BotServiceMessageButton(
                    title='Темы уроков',
                    callback_data=ShowItemsListCallbackData(i_t='T', i_f=None, page=1),
                ),
                BotServiceMessageButton(
                    title='Отчёты',
                    callback_data=ShowItemsListCallbackData(i_t='R', i_f=None, page=1),
                ),
                BotServiceMessageButton(
                    title='Составить отчёт',
                    callback_data=ReportBuilder1CallbackData(),
                ),
            ],
        )

    def delete_one_item(self, data: DeleteOneItemCallbackData) -> BotServiceMessage:
        if data.i_t == 'S':
            text = 'Подтвердите удаление студента'
        elif data.i_t == 'T':
            text = 'Подтвердите удаление темы'

        return BotServiceMessage(
            text=text,
            buttons=[
                BotServiceMessageButton(
                    title='Удалить',
                    callback_data=DeleteConfirmedItemCallbackData(
                        i_t=data.i_t,
                        page=data.page,
                        i_id=data.i_id,
                    ),
                ),
                BotServiceMessageButton(
                    title='Назад',
                    callback_data=ShowOneItemCallbackData(
                        i_t=data.i_t, page=data.page, i_f=None, i_id=data.i_id
                    ),
                ),
            ],
        )

    def delete_confirmed_one_item(
        self, data: DeleteConfirmedItemCallbackData
    ) -> BotServiceMessage:
        print('def delete_confirmed_one_item -> data:', data)

        if data.i_t == 'S':
            if self.student_storage.delete_student(data.i_id):
                text = 'Студент удалён'
            else:
                text = 'Студент не найден'
        elif data.i_t == 'T':
            if self.topic_storage.delete_topic(data.i_id):
                text = 'Тема удалена'
            else:
                text = 'Тема не найдена'

        return BotServiceMessage(
            text=text,
            buttons=[
                BotServiceMessageButton(
                    title='Назад',
                    callback_data=ShowItemsListCallbackData(
                        i_t=data.i_t, i_f=None, page=data.page
                    ),
                ),
            ],
        )

    def show_one_item(self, data: ShowOneItemCallbackData) -> BotServiceMessage:
        print('def show_one_item -> data:', data)
        go_back_button = BotServiceMessageButton(
            title='Назад',
            callback_data=ShowItemsListCallbackData(
                i_t=data.i_t, page=data.page, i_f=data.i_f, i_id=data.i_id
            ),
        )

        if data.i_t == 'S':
            if student := self.student_storage.get_student_by_id(data.i_id):
                text = f'ФИО: {student.name}\nРодитель id: {student.parent_id if student.parent_id else 'отсутсвует'}'
            else:
                text = 'Студент не найден'

            return BotServiceMessage(
                text=text,
                buttons=[
                    BotServiceMessageButton(
                        title='Отчёты',
                        callback_data=ShowItemsListCallbackData(
                            i_t='R', page=data.page, i_f=data.i_id
                        ),
                    ),
                    BotServiceMessageButton(
                        title='Удалить',
                        callback_data=DeleteOneItemCallbackData(
                            i_t=data.i_t,
                            page=data.page,
                            i_id=data.i_id,
                        ),
                    ),
                    BotServiceMessageButton(
                        title='Изменить ФИО',
                        callback_data=UpdateStudentNameCallbackData(
                            page=data.page, student_id=data.i_id
                        ),
                    ),
                    BotServiceMessageButton(
                        title='Изменить id родителя',
                        callback_data=AddParentIdToStudentCallbackData(
                            page=data.page, student_id=data.i_id
                        ),
                    ),
                    go_back_button,
                ],
            )

        elif data.i_t == 'R':
            if report := self.report_storage.get_report_by_id(data.i_id):
                if student := self.student_storage.get_student_by_id(report.student_id):
                    text = self.format_report_text(report)
                else:
                    text = 'Студент не найден'
            else:
                text = 'Отчёт не найден.'

            return BotServiceMessage(text=text, buttons=[go_back_button])

        elif data.i_t == 'T':
            if topic := self.topic_storage.get_topic_by_id(data.i_id):
                text = topic.topic
            else:
                text = 'Тема не найдена.'

            return BotServiceMessage(
                text=text,
                buttons=[
                    BotServiceMessageButton(
                        title='Удалить',
                        callback_data=DeleteOneItemCallbackData(
                            i_t=data.i_t,
                            page=data.page,
                            i_id=data.i_id,
                        ),
                    ),
                    go_back_button,
                ],
            )

    def show_items_list(self, data: ShowItemsListCallbackData) -> BotServiceMessage:
        if data.i_t == 'S':
            formatted_items = [
                FormattedPaginationItem(title=student.name, id=student.student_id)
                for student in self.student_storage.list_students(order_by='name')
            ]
            text = 'Выберите студента:'
            extra_buttons = [
                BotServiceMessageButton(
                    title='Добавить студента',
                    callback_data=CreateStudentCallbackData(page=data.page),
                )
            ]
            row_width = 2

        elif data.i_t == 'R':
            if data.i_f:
                reports_list = self.report_storage.list_reports_by_student_id(
                    student_id=data.i_f, order_by='lesson_date', descending=True
                )
                extra_buttons = [
                    BotServiceMessageButton(
                        title='К студентам',
                        callback_data=ShowItemsListCallbackData(
                            i_t='S', i_f=data.i_f, page=data.page
                        ),
                    )
                ]
            else:
                reports_list = self.report_storage.list_reports(
                    order_by='lesson_date', descending=True
                )
                extra_buttons = [
                    BotServiceMessageButton(
                        title='Отправить сохранённые отчёты',
                        callback_data=SendSavedReportsCallbackData(),
                    )
                ]

            formatted_items = [
                FormattedPaginationItem(
                    title=f'{report.lesson_date.strftime('%d-%m-%Y')} — {student.name}',
                    id=report.report_id,
                )
                for report in reports_list
                if (
                    student := self.student_storage.get_student_by_id(report.student_id)
                )
            ]
            text = 'Выберите отчёт:'
            row_width = 1

        elif data.i_t == 'T':
            formatted_items = [
                FormattedPaginationItem(title=topic.topic, id=topic.topic_id)
                for topic in self.topic_storage.list_topics(order_by='topic')
            ]
            text = 'Выберите тему:'
            extra_buttons = [
                BotServiceMessageButton(
                    title='Добавить тему',
                    callback_data=CreateTopicCallbackData(page=data.page),
                )
            ]
            row_width = 1

        pagination_result = paginate(items=formatted_items, data=data, page_size=10)

        buttons = [
            BotServiceMessageButton(
                title=item['title'],
                callback_data=ShowOneItemCallbackData(
                    i_t=data.i_t,
                    page=data.page,
                    i_f=data.i_f,
                    i_id=item['id'],
                ),
            )
            for item in pagination_result.items
        ]

        if not (pagination_result.is_first_page and pagination_result.is_last_page):
            if not pagination_result.is_first_page:
                buttons.append(
                    BotServiceMessageButton(
                        title='Назад',
                        callback_data=ShowItemsListCallbackData(
                            i_t=data.i_t, i_f=None, page=data.page - 1
                        ),
                    )
                )

            if not pagination_result.is_last_page:
                buttons.append(
                    BotServiceMessageButton(
                        title='Вперёд',
                        callback_data=ShowItemsListCallbackData(
                            i_t=data.i_t, i_f=None, page=data.page + 1
                        ),
                    )
                )

        buttons += extra_buttons
        buttons.append(
            BotServiceMessageButton(
                title='В меню', callback_data=GoBackToAdminPanelCallbackData()
            )
        )
        return BotServiceMessage(text=text, buttons=buttons, row_width=row_width)

    def create_topic(
        self, data: CreateTopicCallbackData
    ) -> list[BotServiceMessage | BotServiceRegisterNextMessageHandler]:
        def process_topic_name(message_text: str) -> list[BotServiceMessage]:
            topic_id = self.topic_storage.add_topic(message_text)
            return [
                self.show_one_item(
                    ShowOneItemCallbackData(
                        i_t='T', page=data.page, i_f=None, i_id=topic_id
                    )
                )
            ]

        return [
            BotServiceMessage(text='Введите название темы:'),
            BotServiceRegisterNextMessageHandler(process_topic_name),
        ]

    def create_student(
        self, data: CreateStudentCallbackData
    ) -> list[BotServiceMessage | BotServiceRegisterNextMessageHandler]:
        def process_student_name_input(message_text: str) -> list[BotServiceMessage]:
            student_name = ' '.join(
                map(lambda word: word.capitalize(), message_text.strip().split())
            )
            student_id = self.student_storage.add_student(student_name)
            return [
                self.show_one_item(
                    ShowOneItemCallbackData(
                        i_t='S', page=data.page, i_f=None, i_id=student_id
                    )
                )
            ]

        return [
            BotServiceMessage(text='Введите ФИО студента:'),
            BotServiceRegisterNextMessageHandler(process_student_name_input),
        ]

    def add_parent_id_to_student(
        self, data: AddParentIdToStudentCallbackData, student_id: int
    ) -> list[BotServiceMessage | BotServiceRegisterNextMessageHandler]:
        def process_student_parent_id_input(
            message_text: str,
        ) -> list[BotServiceMessage]:
            try:
                parent_id = int(message_text)
            except ValueError:
                return [
                    BotServiceMessage(text='Введите id родителя:'),
                    BotServiceRegisterNextMessageHandler(
                        process_student_parent_id_input
                    ),
                ]
            self.student_storage.add_parent_id_to_student(
                student_id=student_id, parent_id=parent_id
            )
            return [
                self.show_one_item(
                    ShowOneItemCallbackData(
                        i_t='S', page=data.page, i_f=None, i_id=student_id
                    )
                )
            ]

        return [
            BotServiceMessage(
                text='Введите id родителя:',
                buttons=[
                    BotServiceMessageButton(
                        title='Назад',
                        callback_data=ShowOneItemCallbackData(
                            i_t='S', page=data.page, i_f=None, i_id=data.student_id
                        ),
                    )
                ],
            ),
            BotServiceRegisterNextMessageHandler(process_student_parent_id_input),
        ]

    def update_student_name(
        self, data: UpdateStudentNameCallbackData
    ) -> list[BotServiceMessage | BotServiceRegisterNextMessageHandler]:
        def process_student_name_input(message_text: str) -> list[BotServiceMessage]:
            self.student_storage.update_student_name(
                student_id=data.student_id, student_name=message_text
            )
            return [
                self.show_one_item(
                    ShowOneItemCallbackData(
                        i_t='S',
                        page=data.page,
                        i_f=None,
                        i_id=data.student_id,
                    )
                )
            ]

        return [
            BotServiceMessage(
                text='Введите имя и фамилию:',
                buttons=[
                    BotServiceMessageButton(
                        title='Назад',
                        callback_data=ShowOneItemCallbackData(
                            i_t='S', page=data.page, i_f=None, i_id=data.student_id
                        ),
                    )
                ],
            ),
            BotServiceRegisterNextMessageHandler(process_student_name_input),
        ]

    def build_report_1_lesson_date_setting(self) -> BotServiceMessage:
        return BotServiceMessage(
            text='Выберите дату:',
            buttons=[
                BotServiceMessageButton(
                    title='Сегодня',
                    callback_data=ReportBuilder1SetValueFromButtonCallbackData(
                        lesson_day='today'
                    ),
                ),
                BotServiceMessageButton(
                    title='Вчера',
                    callback_data=ReportBuilder1SetValueFromButtonCallbackData(
                        lesson_day='yesterday'
                    ),
                ),
                BotServiceMessageButton(
                    title='Ввести дату:',
                    callback_data=ReportBuilder1EnterManuallyCallbackData(),
                ),
                BotServiceMessageButton(
                    title='В меню', callback_data=GoBackToAdminPanelCallbackData()
                ),
            ],
        )

    def build_report_1_lesson_date_from_button(
        self, lesson_day: str
    ) -> list[BotServiceMessage | BotServiceRegisterNextMessageHandler]:
        if lesson_day == 'today':
            lesson_date = datetime.today()
        elif lesson_day == 'yesterday':
            lesson_date = datetime.today() - timedelta(days=1)
        self.report_builder.set_lesson_date_1(lesson_date=lesson_date.date())
        return [
            self.build_report_2_topic_setting(
                data=ReportBuilderShowItemListCallbackData(i_t='T', page=1),
            )
        ]

    def build_report_1_manual(
        self,
    ) -> list[BotServiceMessage | BotServiceRegisterNextMessageHandler]:
        def process_lesson_date(
            message_text: str,
        ) -> list[BotServiceMessage | BotServiceRegisterNextMessageHandler]:
            try:
                lesson_date = datetime.strptime(message_text, '%d-%m-%Y')
            except ValueError:
                return [
                    BotServiceMessage(
                        text="Введите дату в корректном формате ('ДД-ММ-ГГГГ'):",
                        buttons=[
                            BotServiceMessageButton(
                                title='В меню',
                                callback_data=GoBackToAdminPanelCallbackData(),
                            )
                        ],
                    ),
                    BotServiceRegisterNextMessageHandler(process_lesson_date),
                ]

            self.report_builder.set_lesson_date_1(lesson_date=lesson_date)
            return [
                self.build_report_2_topic_setting(
                    data=ReportBuilderShowItemListCallbackData(i_t='T', page=1),
                )
            ]

        return [
            BotServiceMessage(
                text="Введите дату в формате ('ДД-ММ-ГГГГ'):",
                buttons=[
                    BotServiceMessageButton(
                        title='В меню', callback_data=GoBackToAdminPanelCallbackData()
                    )
                ],
            ),
            BotServiceRegisterNextMessageHandler(process_lesson_date),
        ]

    def build_report_2_topic_setting(
        self,
        data: ReportBuilderShowItemListCallbackData,
    ) -> BotServiceMessage:
        formatted_items = [
            FormattedPaginationItem(title=topic.topic, id=topic.topic_id)
            for topic in self.topic_storage.list_topics(order_by='topic')
        ]

        pagination_result = paginate(items=formatted_items, data=data, page_size=10)

        buttons = [
            BotServiceMessageButton(
                title=item['title'],
                callback_data=ReportBuilderChooseItemListCallbackData(
                    i_t=data.i_t,
                    i_id=item['id'],
                ),
            )
            for item in pagination_result.items
        ]

        if not pagination_result.is_first_page:
            buttons.append(
                BotServiceMessageButton(
                    title='Назад',
                    callback_data=ReportBuilderShowItemListCallbackData(
                        i_t=data.i_t, page=data.page - 1
                    ),
                )
            )

        if not pagination_result.is_last_page:
            buttons.append(
                BotServiceMessageButton(
                    title='Вперёд',
                    callback_data=ReportBuilderShowItemListCallbackData(
                        i_t=data.i_t, page=data.page + 1
                    ),
                )
            )

        buttons.append(
            BotServiceMessageButton(
                title='В меню', callback_data=GoBackToAdminPanelCallbackData()
            )
        )

        return BotServiceMessage(text='Выберите тему:', buttons=buttons, row_width=2)

    def build_report_3_student_setting(
        self, data: ReportBuilderShowItemListCallbackData
    ) -> BotServiceMessage:
        formatted_items = [
            FormattedPaginationItem(title=student.name, id=student.student_id)
            for student in self.student_storage.list_students(order_by='name')
        ]

        pagination_result = paginate(items=formatted_items, data=data, page_size=10)

        buttons = [
            BotServiceMessageButton(
                title=item['title'],
                callback_data=ReportBuilderChooseItemListCallbackData(
                    i_t=data.i_t,
                    i_id=item['id'],
                ),
            )
            for item in pagination_result.items
        ]

        if not pagination_result.is_first_page:
            buttons.append(
                BotServiceMessageButton(
                    title='Назад',
                    callback_data=ReportBuilderShowItemListCallbackData(
                        i_t=data.i_t, page=data.page - 1
                    ),
                )
            )

        if not pagination_result.is_last_page:
            buttons.append(
                BotServiceMessageButton(
                    title='Вперёд',
                    callback_data=ReportBuilderShowItemListCallbackData(
                        i_t=data.i_t, page=data.page + 1
                    ),
                )
            )

        buttons.append(
            BotServiceMessageButton(
                title='В меню', callback_data=GoBackToAdminPanelCallbackData()
            )
        )

        return BotServiceMessage(text='Выберите студента:', buttons=buttons)

    def build_report_5_homework_status_setting(self) -> BotServiceMessage:
        return BotServiceMessage(
            text='Домашнее задание',
            buttons=[
                BotServiceMessageButton(
                    title='Выполнено',
                    callback_data=ReportBuilder5SetHomeworkStatusCallbackData(
                        homework_status=0
                    ),
                ),
                BotServiceMessageButton(
                    title='Выполнено частично',
                    callback_data=ReportBuilder5SetHomeworkStatusCallbackData(
                        homework_status=1
                    ),
                ),
                BotServiceMessageButton(
                    title='Не выполнено',
                    callback_data=ReportBuilder5SetHomeworkStatusCallbackData(
                        homework_status=2
                    ),
                ),
                BotServiceMessageButton(
                    title='В меню', callback_data=GoBackToAdminPanelCallbackData()
                ),
            ],
        )

    def build_report_6_is_proactive_setting(self) -> BotServiceMessage:
        return BotServiceMessage(
            text='Активность на занятии',
            buttons=[
                BotServiceMessageButton(
                    title='Сильная',
                    callback_data=ReportBuilder6SetIsProactiveCallbackData(is_active=1),
                ),
                BotServiceMessageButton(
                    title='Слабая',
                    callback_data=ReportBuilder6SetIsProactiveCallbackData(is_active=0),
                ),
                BotServiceMessageButton(
                    title='В меню', callback_data=GoBackToAdminPanelCallbackData()
                ),
            ],
        )

    def build_report_7_payment_status_setting(self) -> BotServiceMessage:
        return BotServiceMessage(
            text='Занятие',
            buttons=[
                BotServiceMessageButton(
                    title='Оплачено',
                    callback_data=ReportBuilder7SetIsPaidCallbackData(payment_status=1),
                ),
                BotServiceMessageButton(
                    title='Не оплачено',
                    callback_data=ReportBuilder7SetIsPaidCallbackData(payment_status=0),
                ),
                BotServiceMessageButton(
                    title='В меню', callback_data=GoBackToAdminPanelCallbackData()
                ),
            ],
        )

    def build_report_8_ask_comment(self) -> BotServiceMessage:
        return BotServiceMessage(
            text='Добавить комментарий?',
            buttons=[
                BotServiceMessageButton(
                    title='Добавить',
                    callback_data=ReportBuilder8AddCommentQuestionCallbackData(),
                ),
                BotServiceMessageButton(
                    title='Пропустить',
                    callback_data=ReportBuilderShowReportPreviewCallbackData(),
                ),
                BotServiceMessageButton(
                    title='В меню', callback_data=GoBackToAdminPanelCallbackData()
                ),
            ],
        )

    def build_report_8_get_comment(
        self,
    ) -> list[BotServiceMessage | BotServiceRegisterNextMessageHandler]:
        def process_comment_input(message_text: str) -> BotServiceMessage:
            self.report_builder.set_comment_8(message_text)
            return [self.build_report_preview()]

        return [
            BotServiceMessage(text='Введите комментарий:', buttons=[]),
            BotServiceRegisterNextMessageHandler(callback=process_comment_input),
        ]

    def format_report_text(self, report: Report | ReportData) -> str:
        topic = self.topic_storage.get_topic_by_id(report.topic_id)
        student = self.student_storage.get_student_by_id(report.student_id)
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

    def build_report_preview(self) -> BotServiceMessage:
        report = self.report_builder.preview_complete_report()
        if parent_id := self.student_storage.get_parent_id(
            student_id=report.student_id
        ):
            button_send_and_save_title = 'Сохранить и отправить отчёт'
        else:
            button_send_and_save_title = 'Сохранить отчёт'

        text = self.format_report_text(report)
        return BotServiceMessage(
            text=text,
            buttons=[
                BotServiceMessageButton(
                    title='В меню', callback_data=GoBackToAdminPanelCallbackData()
                ),
                BotServiceMessageButton(
                    title='Новый отчёт', callback_data=ReportBuilder1CallbackData()
                ),
                BotServiceMessageButton(
                    title=button_send_and_save_title,
                    callback_data=SaveConfirmedReportCallbackData(parent_id=parent_id),
                ),
            ],
        )

    def save_report(self, parent_id: int | None = None) -> BotServiceMessage:
        complete_report = self.report_builder.complete_report()
        self.report_storage.add_report(
            Report(
                lesson_date=complete_report.lesson_date,
                lesson_count=complete_report.lesson_count,
                topic_id=complete_report.topic_id,
                student_id=complete_report.student_id,
                homework_status=complete_report.homework_status,
                is_proactive=complete_report.is_proactive,
                is_paid=complete_report.is_paid,
                is_sent=True if parent_id else False,
                comment=complete_report.comment,
            )
        )
        return complete_report

    def send_report(self, complete_report: ReportData) -> BotServiceMessage:
        text = self.format_report_text(complete_report)
        return [BotServiceMessage(text=text, buttons=[])]

    def send_saved_reports(self) -> list[tuple[BotServiceMessage, int, int]]:
        result = []
        for report in self.report_storage.get_saved_reports():
            if parent_id := self.student_storage.get_parent_id(report.student_id):
                result += [
                    (
                        BotServiceMessage(text=self.format_report_text(report)),
                        report.report_id,
                        parent_id,
                    )
                ]
        return result

    def get_error_message_temp_report_must_be_filled(self) -> BotServiceMessage:
        return BotServiceMessage(text='Отчёт не полный. Создайте с самого начала.')
