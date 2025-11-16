from src.core.postgres import async_session_maker
from src.repositories.auth import AuthRepository
from src.repositories.user import UserRepository
from src.repositories.role import RoleRepository
from src.repositories.registration import RegistrationRequestRepository
from src.repositories.course import CourseRepository
from src.repositories.course_topic import CourseTopicRepository
from src.repositories.course_material import CourseMaterialRepository
from src.repositories.group import GroupRepository
from src.repositories.enrollment import EnrollmentRepository
from src.repositories.event import EventRepository
from src.repositories.reflection import ReflectionRepository
from src.repositories.question_set import QuestionSetRepository
from src.repositories.question import QuestionRepository
from src.repositories.reflection_answer import ReflectionAnswerRepository
from src.repositories.support_question import SupportQuestionRepository


class UnitOfWork:
    def __init__(self):
        self.session_factory = async_session_maker

    async def __aenter__(self):
        self.session = self.session_factory()
        self.auth = AuthRepository(self.session)
        self.user = UserRepository(self.session)
        self.role = RoleRepository(self.session)
        self.registration_request = RegistrationRequestRepository(self.session)
        self.course = CourseRepository(self.session)
        self.course_topic = CourseTopicRepository(self.session)
        self.course_material = CourseMaterialRepository(self.session)
        self.group = GroupRepository(self.session)
        self.enrollment = EnrollmentRepository(self.session)
        self.event = EventRepository(self.session)
        self.reflection = ReflectionRepository(self.session)
        self.question_set = QuestionSetRepository(self.session)
        self.question = QuestionRepository(self.session)
        self.reflection_answer = ReflectionAnswerRepository(self.session)
        self.support_question = SupportQuestionRepository(self.session)

    async def __aexit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            await self.rollback()
        else:
            await self.commit()
        await self.session.close()

    async def commit(self):
        await self.session.commit()

    async def rollback(self):
        await self.session.rollback()