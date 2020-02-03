from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text

from b import Base

class ModQueueItem(Base):
    __tablename__ = 'modqueue'
    __table_args__ = {'postgresql_partition_by':'range(date)'}
    id = Column(String, primary_key=True)
    posttype = Column(String)
    date = Column(DateTime, primary_key=True)
    link_title = Column(String)
    link_id = Column(String)
    author = Column(String)
    edited = Column(String)
    body = Column(String)
    permalink = Column(String)

class ModLog(Base):
    __tablename__ = 'modlogs'
    __table_args__ = {'postgresql_partition_by':'range(date)'}
    id = Column(String, primary_key=True)
    target_body = Column(String)
    mod_id36 = Column(String)
    date = Column(DateTime, primary_key=True)
    created_utc = Column(Integer)
    subreddit = Column(String)
    target_title = Column(String)
    target_permalink = Column(String)
    details = Column(String)
    action = Column(String)
    target_author = Column(String)
    target_fullname = Column(String)
    sr_id36 = Column(String)
    mod = Column(String)

class DiscordAction(Base):
    __tablename__ = 'discordactions'
    __table_args__ = {'postgresql_partition_by':'range(date)'}
    id = Column(String, primary_key=True)
    action = Column(String, primary_key=True)
    date = Column(DateTime, primary_key=True)
    link = Column(String)
    text = Column(Text)
    target_id = Column(String)
    target_type = Column(String)
    completed = Column(Boolean, default=False)
    reactcompleted = Column(Boolean, default=False)
    messageID = Column(String)
    target_user = Column(String)
    target_channel = Column(String)

class Report(Base):
    __tablename__ = 'reports'
    __table_args__ = {'postgresql_partition_by':'range(date)'}
    id = Column(String, primary_key=True)
    date = Column(DateTime, primary_key=True)
    count = Column(String, primary_key=True)
    reason = Column(String, nullable=False)

class ModMailConversation(Base):
    __tablename__ = 'modmailconversations'
    __table_args__ = {'postgresql_partition_by':'range(date)'}
    id = Column(String, primary_key=True)
    participant = Column(String)
    subject = Column(String)
    date = Column(DateTime, primary_key=True)

class ModMailMessage(Base):
    __tablename__ = 'modmailmessages'
    __table_args__ = {'postgresql_partition_by':'range(date)'}
    id = Column(String, primary_key=True)
    conversation_id = Column(String, primary_key=True)
    body = Column(String)
    author = Column(String)
    date = Column(DateTime, primary_key=True)
