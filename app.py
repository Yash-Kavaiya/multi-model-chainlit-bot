import google.generativeai as genai
from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser
from langchain.schema.runnable import Runnable
from langchain.schema.runnable.config import RunnableConfig
import getpass
import os
from langchain_google_genai import ChatGoogleGenerativeAI
import chainlit as cl
from PIL import Image
import io

if "GOOGLE_API_KEY" not in os.environ:
    os.environ["GOOGLE_API_KEY"] = getpass.getpass("Provide your Google API Key")
import chainlit as cl
import os

@cl.on_chat_start
async def on_chat_start():
    text_model = ChatGoogleGenerativeAI(model="gemini-pro", convert_system_message_to_human=True)
    vision_model = ChatGoogleGenerativeAI(model="gemini-pro-vision", convert_system_message_to_human=True)
    
    text_prompt = ChatPromptTemplate.from_messages([
        ("system", "You're a very knowledgeable historian who provides accurate and eloquent answers to historical questions."),
        ("human", "{question}")
    ])
    
    vision_prompt = ChatPromptTemplate.from_messages([
        ("system", "You're a very knowledgeable historian who can analyze historical images and provide accurate and eloquent descriptions and context."),
        ("human", "Analyze this historical image: {image_description}")
    ])
    
    text_runnable = text_prompt | text_model | StrOutputParser()
    vision_runnable = vision_prompt | vision_model | StrOutputParser()
    
    cl.user_session.set("text_runnable", text_runnable)
    cl.user_session.set("vision_runnable", vision_runnable)

    # Inform the user about file upload capability
    await cl.Message(content="You can upload files by attaching them to your messages. Supported file types include images, PDFs, TXT, and CSV files.").send()
from PIL import Image
import io

@cl.on_message
async def on_message(message: cl.Message):
    text_runnable = cl.user_session.get("text_runnable")
    vision_runnable = cl.user_session.get("vision_runnable")
    
    msg = cl.Message(content="")
    
    if message.elements:
        for element in message.elements:
            if isinstance(element, cl.File):
                if element.mime.startswith("image/"):
                    image = Image.open(io.BytesIO(element.content))
                    async for chunk in vision_runnable.astream(
                        {"image_description": image},
                        config=RunnableConfig(callbacks=[cl.LangchainCallbackHandler()]),
                    ):
                        await msg.stream_token(chunk)
                elif element.mime in ["application/pdf", "text/plain", "text/csv"]:
                    # Handle PDF, TXT, and CSV files
                    await msg.stream_token(f"Processing {element.name} ({element.mime})...")
                    # Implement file processing logic here
                    # For now, we'll just acknowledge the upload
                    await msg.stream_token(f"\nFile {element.name} received. Processing of {element.mime} files is not yet implemented.")
                else:
                    await msg.stream_token(f"Unsupported file type: {element.mime}")
    else:
        async for chunk in text_runnable.astream(
            {"question": message.content},
            config=RunnableConfig(callbacks=[cl.LangchainCallbackHandler()]),
        ):
            await msg.stream_token(chunk)
    
    await msg.send()