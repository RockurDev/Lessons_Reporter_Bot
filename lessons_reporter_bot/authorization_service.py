from dataclasses import dataclass

from lessons_reporter_bot.settings import UserId


@dataclass
class AuthorizationService:
    superusers: list[UserId]

    def has_teacher_access(self, user_id: UserId) -> bool:
        return user_id in self.superusers
