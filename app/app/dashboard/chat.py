import os

from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import SystemMessage
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_openai import ChatOpenAI
from langchain_core.runnables.history import RunnableWithMessageHistory
from redis import StrictRedis

REDIS_SERVER = os.getenv("REDIS_SERVER", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API = os.getenv("OPENROUTER_API")

# Initialize Redis client
redis_client = StrictRedis(host=REDIS_SERVER, port=REDIS_PORT, db=REDIS_DB)

def forget_conversation(user):
    session_id = f"chat_session_{user.id}"
    
    try:
        # Clear the Redis chat history for this session
        message_history = RedisChatMessageHistory(session_id=session_id, url=f"redis://{REDIS_SERVER}:{REDIS_PORT}/{REDIS_DB}")
        message_history.clear()
        
        return True
    except Exception as e:
        return False
    
def do_chat(human_input, llm_model, session_id):
    # Initialize chat model
    llm = ChatOpenAI(base_url=OPENROUTER_API, api_key=API_KEY, model_name=llm_model)

    # Create prompt template
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content="You are a helpful AI assistant."),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}")
    ])

    # Set up message history with Redis
    message_history = RedisChatMessageHistory(session_id=session_id, url=f"redis://{REDIS_SERVER}:{REDIS_PORT}/{REDIS_DB}")

    # Create runnable chain
    chain = prompt | llm

    # Create runnable with message history
    runnable_with_history = RunnableWithMessageHistory(
        chain,
        lambda session_id: message_history,
        input_messages_key="input",
        history_messages_key="history"
    )

    # Run the conversation
    response = runnable_with_history.invoke(
        {"input": human_input},
        config={"configurable": {"session_id": session_id}}
    )

    return response.content
