import os
from fastapi import FastAPI, Request, Form
from fastapi.responses import PlainTextResponse
from twilio.rest import Client
from dotenv import load_dotenv

from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

# Load .env variables
load_dotenv()

# FastAPI app
app = FastAPI()

# Gemini LLM setup
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.7
)

# Twilio credentials
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_whatsapp_number = "whatsapp:+14155238886"
client = Client(account_sid, auth_token)

# Prompt template
prompt_template = PromptTemplate.from_template("""
You are a helpful travel assistant. Answer concisely.
{history}
Human: {input}
AI:""")

# Session memory
session_memories = {}

@app.post('/whatsapp', response_class=PlainTextResponse)
async def whatsapp_webhook(
    request: Request,
    Body: str = Form(...),
    From: str = Form(...)
):
    print(f"[{From}] {Body}")

    # Normalize the message
    user_input = Body.strip().lower()

    # Greeting intent check
    greeting_keywords = {"hi", "hello", "hey", "hii", "heyy"}
    if user_input in greeting_keywords:
        welcome_msg = (
            "Hi, I am *TravelMate AI* – your smart travel assistant! 🌍✈️\n"
            "I can help you:\n"
            "• Plan your trip 🧳\n"
            "• Find flights and hotels 🏨\n"
            "• Suggest places to visit 📍\n"
            "• And answer all your travel questions!\n\n"
            "How can I assist you today?"
        )

        try:
            message = client.messages.create(
                from_=twilio_whatsapp_number,
                body=welcome_msg,
                to=From
            )
            print(f"Sent welcome message SID: {message.sid}")
        except Exception as e:
            print("Failed to send welcome message:", e)

        return "OK"

    # Maintain session per user
    session_id = From
    if session_id not in session_memories:
        session_memories[session_id] = ConversationBufferMemory(
            memory_key="history", input_key="input", return_messages=False
        )

    memory = session_memories[session_id]

    chain = ConversationChain(
        llm=llm,
        memory=memory,
        prompt=prompt_template,
        verbose=False
    )

    # Run the conversation chain
    gemini_response = chain.run(user_input)

    # Simple logic to trigger a template message (customize as needed)
    date = "12/1"
    time = "3pm"

    if "appointment" in gemini_response.lower():
        try:
            message = client.messages.create(
                from_=twilio_whatsapp_number,
                content_sid="HXb5b62575e6e4ff6129ad7c8efe1f983e",  # Replace with real content SID
                content_variables=f'{{"1":"{date}","2":"{time}"}}',
                to=From
            )
            print(f"Sent template message SID: {message.sid}")
        except Exception as e:
            print("Failed to send template message:", e)
    else:
        try:
            message = client.messages.create(
                from_=twilio_whatsapp_number,
                body=gemini_response,
                to=From
            )
            print(f"Sent normal message SID: {message.sid}")
        except Exception as e:
            print("Failed to send fallback message:", e)

    return "OK"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)
