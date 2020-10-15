import time

from sqlalchemy import create_engine, func, or_
from sqlalchemy.orm import sessionmaker, Session

from json_value_history.models import Base, AttributeSave, DiffTypeEnum, \
    AttributeSaveHistory


class SessionWrapper:
    def __init__(self, session):
        self.session = session

    def __enter__(self) -> Session:
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.commit()


class Structure:
    def __init__(self, body, attr):
        self.body = body
        self.attr = attr

    def __getitem__(self, item):
        return self.body[item]


class SaveController:
    def __init__(self):
        self._engine = create_engine('sqlite:///:memory:', echo=True)
        Base.metadata.create_all(self._engine)
        self._session_maker = sessionmaker(bind=self._engine)

    def _convert_to_attr(self, o, attr=()):
        if isinstance(o, dict):
            for k, v in o.items():
                yield from self._convert_to_attr(v, attr + (k,))
        elif isinstance(o, list):
            for k, v in enumerate(o):
                yield from self._convert_to_attr(v, attr + (k,))
        else:
            yield attr, o

    def _create_session(self):
        return SessionWrapper(self._session_maker())

    def init(self, o):
        with self._create_session() as session:
            session.add_all([
                AttributeSave(attr=attr, value=value)
                for attr, value in self._convert_to_attr(o)
            ])

    def _is_array(self, o):
        for k in o:
            return isinstance(k, int)
        return False

    def _load_attr(self, session):
        result = {}
        for attr_row in session.query(AttributeSave).filter(
            or_(
                AttributeSave.diff_type.is_(None),
                AttributeSave.diff_type != DiffTypeEnum.CREATE
            )
        ):
            current = result
            for attr in attr_row.attr[:-1]:
                current = current.setdefault(attr, {})
            current[attr_row.attr[-1]] = attr_row
        return result

    def _convert_to_object(self, o):
        if isinstance(o, AttributeSave):
            return o.value
        elif self._is_array(o):
            return [
                self._convert_to_object(v)
                for k, v in sorted(o.items())
            ]
        else:
            return {
                k: self._convert_to_object(v)
                for k, v in o.items()
            }

    def _convert_to_structure(self, o, attr=()):
        if isinstance(o, AttributeSave):
            return Structure(o, attr)
        else:
            return Structure({
                k: self._convert_to_structure(v, attr + (k, ))
                for k, v in o.items()
            }, attr)

    def get_latest(self):
        with self._create_session() as session:
            return self._convert_to_object(self._load_attr(session))

    def get_latest_with_structure(self):
        with self._create_session() as session:
            return self._convert_to_structure(self._load_attr(session))

    def _get_next_index(self, session, attr):
        # 이건 좀 최적화 필요할 듯
        length = len(attr)
        last_index = 0
        for attr_row in session.query(AttributeSave).filter(AttributeSave.attr > attr):
            if tuple(attr_row.attr[:length]) == attr:
                last_index = length+1
        return last_index

    def append(self, attr, value):
        with self._create_session() as session:
            index = self._get_next_index(session, attr)
            session.add_all([
                AttributeSave(
                    before_submit_attr=attr,
                    before_submit_value=value,
                    diff_type=DiffTypeEnum.CREATE
                )
                for attr, value in self._convert_to_attr(value, attr + (index, ))
            ])

    def change(self, attr, value):
        with self._create_session() as session:
            attr_row: AttributeSave = session.query(AttributeSave).filter(AttributeSave.attr == attr).first()
            attr_row.before_submit_value = value
            if attr_row.diff_type != DiffTypeEnum.CREATE:
                attr_row.diff_type = DiffTypeEnum.EDIT

    def submit(self):
        with self._create_session() as session:
            version = int(time.time())
            for attr_row in session.query(AttributeSave).filter(AttributeSave.diff_type.isnot(None)):
                history = AttributeSaveHistory(
                    prev_attr=attr_row.attr, prev_value=attr_row.value,
                    next_attr=attr_row.before_submit_attr or attr_row.attr,
                    next_value=attr_row.before_submit_value or attr_row.value,
                    diff_type=attr_row.diff_type,
                    version=version
                )
                attr_row.attr = history.next_attr
                attr_row.value = history.next_value
                attr_row.before_submit_attr = None
                attr_row.before_submit_value = None
                attr_row.diff_type = None
                attr_row.history.append(history)

    def get_latest_history(self):
        print("get_latest_history")
        with self._create_session() as session:
            version = session.query(
                func.max(AttributeSaveHistory.version)
            ).first()[0]
            if version is not None:
                yield from session.query(AttributeSaveHistory).filter(AttributeSaveHistory.version == version)
