from enum import Enum

from sqlalchemy import Column, Integer, JSON, types, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Attribute(types.TypeDecorator):
    impl = types.Text

    def process_bind_param(self, value, dialect):
        if value:
            return ".".join([
                attr if isinstance(attr, str) else f"{attr:04}"
                for attr in value
            ])

    def process_result_value(self, value, dialect):
        if value:
            return [
                int(attr) if attr.isdigit() else attr
                for attr in value.split('.')
            ]
        else:
            return []

    def copy(self, **kwargs):
        return Attribute()


class DiffTypeEnum:
    CREATE = 1
    EDIT = 2
    DELETE = 3


class AttributeSave(Base):
    __tablename__ = "attribute_save"

    id = Column(Integer(), primary_key=True, autoincrement=True)
    attr = Column(Attribute())
    value = Column(JSON())  # primary저장할 때 int랑 str이랑 구분하려고

    before_submit_attr = Column(JSON())
    before_submit_value = Column(JSON())
    diff_type = Column(Integer())


class AttributeSaveHistory(Base):
    __tablename__ = "attribute_save_history"

    id = Column(Integer(), primary_key=True, autoincrement=True)
    parent_id = Column(Integer(), ForeignKey('attribute_save.id'))
    history = relationship('AttributeSave', backref="history")

    prev_attr = Column(JSON())
    prev_value = Column(JSON())
    next_attr = Column(JSON())
    next_value = Column(JSON())
    diff_type = Column(Integer())
    version = Column(Integer())
