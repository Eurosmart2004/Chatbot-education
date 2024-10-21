import sys
import streamlit as st
import pandas as pd
import numpy as np
from langchain_upstage import ChatUpstage
from langchain_upstage import UpstageEmbeddings
from langchain_chroma import Chroma
from langchain.chains.retrieval import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain.chains.history_aware_retriever import create_history_aware_retriever
import dropbox
import os
from tool import process_resonse, extract_video, extract_weeks, Video
from dotenv import load_dotenv
load_dotenv()

# Dropbox access
DROPBOX_ACCESS_TOKEN = os.getenv('DROPBOX_ACCESS_TOKEN')

# Initialize Dropbox client
dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)

def list_files_in_folder(dropbox_folder_path):
    try:
        files = []
        result = dbx.files_list_folder(dropbox_folder_path)
        files.extend(result.entries)
        while result.has_more:
            result = dbx.files_list_folder_continue(result.cursor)
            files.extend(result.entries)
        return files
    except dropbox.exceptions.ApiError as err:
        print(f"Failed to list folder contents: {err}")
        return []

def download_file_from_dropbox(dropbox_path, local_path):
    try:
        metadata, res = dbx.files_download(path=dropbox_path)
        with open(local_path, "wb") as f:
            f.write(res.content)
    except dropbox.exceptions.ApiError as err:
        print(f"Failed to download file: {err}")

def download_folder_from_dropbox(dropbox_folder_path, local_folder_path):
    files = list_files_in_folder(dropbox_folder_path)
    if not os.path.exists(local_folder_path):
        os.makedirs(local_folder_path)
    for file in files:
        if isinstance(file, dropbox.files.FileMetadata):
            local_file_path = os.path.join(local_folder_path, file.name)
            print(f"Downloading {file.path_lower} to {local_file_path}")
            download_file_from_dropbox(file.path_lower, local_file_path)
        elif isinstance(file, dropbox.files.FolderMetadata):
            new_dropbox_folder_path = file.path_lower
            new_local_folder_path = os.path.join(local_folder_path, file.name)
            download_folder_from_dropbox(new_dropbox_folder_path, new_local_folder_path)

def initialize_courses():
    available_courses = ["COS30019", "COS30043"]
    for course in available_courses:
        dropbox_folder_path = f'/db/{course}'
        local_folder_path = f'./db/{course}'
        if not os.path.exists(local_folder_path):
            print(f"Initializing download for course: {course}")
            download_folder_from_dropbox(dropbox_folder_path, local_folder_path)
        else:
            print(f"Folder {local_folder_path} already exists. Skipping download.")

@st.cache_resource
def load_model():
    llm = ChatUpstage(
        api_key=st.session_state.api_key,
    )
    return llm

def load_retriever(weeks=None):
    local_folder_path = f'./db/{selectedCourse}'
    embeddings = UpstageEmbeddings(
        model="solar-embedding-1-large-query",
        api_key=st.session_state.api_key,
    )
    vectorstorage = Chroma(persist_directory=local_folder_path, embedding_function=embeddings)
    if weeks:
        filter_dict = {"week": {"$in": weeks}}
        retriever = vectorstorage.as_retriever(
            search_type="similarity", 
            search_kwargs={"k": 300,"filter": filter_dict,}
        )
    else:
        retriever = vectorstorage.as_retriever(
            search_type="similarity", 
            search_kwargs={"k": 20}
        )
    return retriever

contextualize_q_system_prompt = (
    "Given a chat history and the latest user question "
    "which might reference context in the chat history, "
    "formulate a standalone question which can be understood "
    "without the chat history. Do NOT answer the question, "
    "just reformulate it if needed and otherwise return it as is."
)

contextualize_q_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", contextualize_q_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ]
)

system_prompt = (
    "You are an assistant for question-answering tasks. "
    "Use the following pieces of retrieved context to answer "
    "the question. \n\n{context}"
    "If there is no context provided, say that you don't have enough information to answer."
    "Otherwise provide a concise answer to the question."
    "\n\n"
)
qa_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ]
)

def should_show_video(text, input, answer):
    llm = load_model()
    response = llm.invoke(f"Is the user query '{input}' about a course? Does the answer in the video '{answer}' support the query? Are the answer and the text '{text}' relevant to the context of the user query? Answer yes or no")

    if 'Yes' in response.content:
        return True

    return False

def process_chat_history(chat_history):
    history = []
    for message in chat_history:
        if isinstance(message, HumanMessage):
            history.append(message)
        if isinstance(message, AIMessage):
            history.append(message)
    return history

def ai_response(user_query):
    try:
        weeks = extract_weeks(user_query)
        print("Week found: ", weeks)
        retriever = load_retriever(weeks)
        print("Retriever loaded")
        history_aware_retriever = create_history_aware_retriever(
            load_model(), retriever, contextualize_q_prompt
        )
        print("History aware retriever created")
        question_answer_chain = create_stuff_documents_chain(load_model(), qa_prompt)
        print("Question answer chain created")
        rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)
        print("RAG chain created")
        responses = rag_chain.stream({
            "chat_history": process_chat_history(st.session_state.chat_history[selectedCourse]),
            "input": user_query
        })
        print("Responses generated")
        for response in responses:
            response = process_resonse(response)
            videos = extract_video(response)
            answer = ''
            if 'answer' in response:
                answer = response['answer']
            yield answer, videos
    except Exception as e:
        st.error(f"An error occurred: {e}")
        yield "", []

if __name__ == '__main__':
    if 'api_key' not in st.session_state:
        st.session_state.api_key = ''

    folder = "./db"
    initialize_courses()
    courseList = []
    for name in os.listdir(folder):
        courseList.append(name)

    api_key = st.sidebar.text_input("Enter your Upstage API key")

    if api_key != "":
        st.session_state.api_key = api_key
        
    selectedCourse = st.sidebar.selectbox("Select a course", courseList, index=0)
    st.title(f'Chatbot {selectedCourse}')

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = {}
        for course in courseList:
            st.session_state.chat_history[course] = []

    for message in st.session_state.chat_history[selectedCourse]:
        if isinstance(message, HumanMessage):
            with st.chat_message("Human"):
                st.markdown(message.content)
        elif isinstance(message, AIMessage):
            with st.chat_message("AI"):
                st.markdown(message.content)
        elif isinstance(message, Video):
            st.video(message.source, start_time=message.start)

    if st.session_state.api_key != '':
        user_query = st.chat_input("Message chatbot")

        if user_query is not None and user_query != "":
            with st.chat_message("Human"):
                st.markdown(user_query)
            st.session_state.chat_history[selectedCourse].append(HumanMessage(user_query))
            with st.spinner("Thinking..."):
                videos = []

                def response_generator():
                    for answer, video_list in ai_response(user_query):
                        videos.extend(video_list)
                        yield answer

                try:
                    answer = st.write_stream(response_generator())
                    st.session_state.chat_history[selectedCourse].append(AIMessage(answer))
                    for video in videos:
                        if should_show_video(video['text'], user_query, answer):
                            st.session_state.chat_history[selectedCourse].append(Video(video['source'], video['Start'], video['End']))
                            st.video(video['source'], start_time=video['Start'])
                except Exception as e:
                    st.error(f"An error occurred: {e}")