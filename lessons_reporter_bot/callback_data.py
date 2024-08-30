from typing import Literal, Optional

import pydantic

"""
Used short expressions forms:
Homework - hw
Repor builder - rb
i - item
i_t - item type
i_f - item filter
s_i - show one item
S - student
R - report
T - topic
"""


class CreateTopicCallbackData(pydantic.BaseModel):
    type: Literal['create_topic'] = 'create_topic'
    page: int


class CreateStudentCallbackData(pydantic.BaseModel):
    type: Literal['create_student'] = 'create_student'
    page: int


class AddParentIdToStudentCallbackData(pydantic.BaseModel):
    type: Literal['add_parent_id'] = 'add_parent_id'
    student_id: int
    page: int


class UpdateStudentNameCallbackData(pydantic.BaseModel):
    type: Literal['update_student_name'] = 'update_student_name'
    student_id: int
    page: int


# Report builder's callback's


class ReportBuilderShowItemListCallbackData(pydantic.BaseModel):
    type: Literal['show_rb_item_list'] = 'show_rb_item_list'
    i_t: Literal['S', 'T']
    page: int


class ReportBuilderChooseItemListCallbackData(pydantic.BaseModel):
    type: Literal['choose_rb_item_list'] = 'choose_rb_item_list'
    i_t: Literal['T', 'S']
    i_id: int


class ReportBuilder1CallbackData(pydantic.BaseModel):
    type: Literal['rb_1'] = 'rb_1'


class ReportBuilder1SetValueFromButtonCallbackData(pydantic.BaseModel):
    type: Literal['rb_1_from_button'] = 'rb_1_from_button'
    lesson_day: str


class ReportBuilder1EnterManuallyCallbackData(pydantic.BaseModel):
    type: Literal['rb_1_manual'] = 'rb_1_manual'


class ReportBuilder3ChooseTopicCallbackData(pydantic.BaseModel):
    type: Literal['rb_3'] = 'rb_3'
    id: int


class ReportBuilder4CallbackData(pydantic.BaseModel):
    type: Literal['rb_4'] = 'rb_4'
    student_id: int


class ReportBuilder5SetHomeworkStatusCallbackData(pydantic.BaseModel):
    type: Literal['rb_5'] = 'rb_5'
    homework_status: int


class ReportBuilder6SetIsProactiveCallbackData(pydantic.BaseModel):
    type: Literal['rb_6'] = 'rb_6'
    is_active: int


class ReportBuilder7SetIsPaidCallbackData(pydantic.BaseModel):
    type: Literal['rb_7'] = 'rb_7'
    payment_status: int


class ReportBuilder8AddCommentQuestionCallbackData(pydantic.BaseModel):
    type: Literal['rb_8'] = 'rb_8'


class ReportBuilderShowReportPreviewCallbackData(pydantic.BaseModel):
    type: Literal['show_preview_report'] = 'show_preview_report'


class SaveConfirmedReportCallbackData(pydantic.BaseModel):
    type: Literal['save_report'] = 'save_report'
    parent_id: int | None


class ShowItemsListCallbackData(pydantic.BaseModel):
    type: Literal['show_items_list'] = 'show_items_list'
    i_t: Literal['S', 'R', 'T']
    i_f: Optional[int]
    page: int


class ShowOneItemCallbackData(pydantic.BaseModel):
    type: Literal['s_i'] = 's_i'
    i_t: Literal['S', 'R', 'T']
    i_f: Optional[int]
    page: int
    i_id: int


class DeleteOneItemCallbackData(pydantic.BaseModel):
    type: Literal['del_item'] = 'del_item'
    i_t: Literal['S', 'T']
    page: int
    i_id: int


class DeleteConfirmedItemCallbackData(pydantic.BaseModel):
    type: Literal['del_c_item'] = 'del_c_item'
    i_t: Literal['S', 'T']
    page: int
    i_id: int


class SendSavedReportsCallbackData(pydantic.BaseModel):
    type: Literal['send_saved_reports'] = 'send_saved_reports'


#  Go back callback
class GoBackToAdminPanelCallbackData(pydantic.BaseModel):
    type: Literal['back_to_admin_panel'] = 'back_to_admin_panel'


AnyCallbackData = (
    # Topic's callback's
    CreateTopicCallbackData
    # Student callback's
    | CreateStudentCallbackData
    | AddParentIdToStudentCallbackData
    | UpdateStudentNameCallbackData
    # Report builder's callback's
    | ReportBuilderShowItemListCallbackData
    | ReportBuilderChooseItemListCallbackData
    | ReportBuilder1CallbackData
    | ReportBuilder1SetValueFromButtonCallbackData
    | ReportBuilder1EnterManuallyCallbackData
    | ReportBuilder3ChooseTopicCallbackData
    | ReportBuilder4CallbackData
    | ReportBuilder5SetHomeworkStatusCallbackData
    | ReportBuilder6SetIsProactiveCallbackData
    | ReportBuilder7SetIsPaidCallbackData
    | ReportBuilder8AddCommentQuestionCallbackData
    | ReportBuilderShowReportPreviewCallbackData
    | SaveConfirmedReportCallbackData
    # Show list, show one, delete, delete with confirmation
    | ShowItemsListCallbackData
    | ShowOneItemCallbackData
    | DeleteOneItemCallbackData
    | DeleteConfirmedItemCallbackData
    | SendSavedReportsCallbackData
    # Go back callback's
    | GoBackToAdminPanelCallbackData
)


any_callback_data_validator: pydantic.TypeAdapter[AnyCallbackData] = (
    pydantic.TypeAdapter(AnyCallbackData)
)
