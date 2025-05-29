from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()
class Client(Base):
    __tablename__ = 'clients'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)

    accounts = relationship("Account", back_populates="client", cascade="all, delete")


class Account(Base):
    __tablename__ = 'accounts'

    client_id = Column(Integer, ForeignKey('clients.id', ondelete="CASCADE"), nullable=False)
    account_number = Column(String(20), primary_key=True)
    balance = Column(Numeric(12, 2), default=0.0)

    client = relationship("Client", back_populates="accounts")


class Transactions(Base):
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True)
    from_account = Column(String(20), ForeignKey('accounts.account_number'))
    to_account = Column(String(20), ForeignKey('accounts.account_number'))
    amount = Column(Numeric(12, 2))
    date = Column(DateTime, default=datetime.now)
