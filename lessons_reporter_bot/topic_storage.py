from typing import List, Optional

from sqlmodel import Session, desc, select

from lessons_reporter_bot.models import Topic
from lessons_reporter_bot.settings import TopicId


class TopicStorage:
    def __init__(self, engine) -> None:
        self.engine = engine

    def count_topics(self) -> int:
        with Session(self.engine) as session:
            return session.exec(select(Topic)).count()

    def add_topic(self, topic: str) -> int:
        new_topic = Topic(topic=topic)
        with Session(self.engine) as session:
            session.add(new_topic)
            session.commit()
            session.refresh(new_topic)
        return new_topic.topic_id

    def list_topics(
        self, order_by: str | None = None, descending: bool = False
    ) -> List[Topic]:
        with Session(self.engine) as session:
            statement = select(Topic)
            if order_by:
                column = getattr(Topic, order_by)
                statement = (
                    statement.order_by(desc(column))
                    if descending
                    else statement.order_by(column)
                )
            return session.exec(statement).all()

    def get_topic_by_id(self, topic_id: TopicId) -> Optional[Topic]:
        with Session(self.engine) as session:
            return session.exec(select(Topic).where(Topic.topic_id == topic_id)).first()

    def delete_topic(self, topic_id: TopicId) -> bool:
        with Session(self.engine) as session:
            topic = session.exec(
                select(Topic).where(Topic.topic_id == topic_id)
            ).first()
            if topic:
                session.delete(topic)
                session.commit()
                return True
            return False
