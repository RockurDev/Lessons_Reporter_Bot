import pydantic_settings

UserId = int
StudentId = int
ParentId = int
ReportId = int
TopicId = int


class Settings(pydantic_settings.BaseSettings):
    model_config = pydantic_settings.SettingsConfigDict(env_file='.env')

    bot_token: str
    superusers: list[UserId]
    database_url: str
