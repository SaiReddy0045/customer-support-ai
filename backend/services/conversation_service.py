from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import Conversation, Message, Customer


def get_or_create_conversation(
    db: Session,
    conversation_id: str | None,
    customer_id: str | None,
) -> Conversation:

    customer = None
    if customer_id:
        customer = db.execute(
            select(Customer).where(Customer.customer_id == customer_id)
        ).scalar_one_or_none()
        if not customer:
            raise ValueError(f"Customer {customer_id} was not found.")

    conversation = None
    if conversation_id:
        conversation = db.execute(
            select(Conversation).where(Conversation.conversation_id == conversation_id)
        ).scalar_one_or_none()

    if conversation:
        if customer and conversation.customer_id != customer.id:
            raise ValueError("Conversation does not belong to this customer.")
        return conversation

    if not customer:
        raise ValueError("A valid customer is required to create a conversation.")

    new_conversation_id = conversation_id or str(uuid4())
    conversation = Conversation(
        conversation_id=new_conversation_id,
        customer_id=customer.id,
    )

    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return conversation


def get_conversation_messages(
    db: Session,
    conversation: Conversation,
) -> list[dict]:

    messages = db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.asc(), Message.id.asc())
    ).scalars().all()

    return [
        {
            "role": message.role,
            "content": message.content,
            "agent": message.agent,
        }
        for message in messages
    ]


def save_message(
    db: Session,
    conversation: Conversation,
    role: str,
    content: str,
    agent: str | None = None,
):
    message = Message(
        conversation_id=conversation.id,
        role=role,
        content=content,
        agent=agent,
    )

    db.add(message)
    conversation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(message)

    return message
