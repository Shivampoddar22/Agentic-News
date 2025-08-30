import streamlit as st
import os
from langchain_groq import ChatGroq
from langchain_community.document_loaders import PyPDFLoader  
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain
from langchain_community.vectorstores import FAISS
import time
import hashlib

from dotenv import load_dotenv
load_dotenv()


@st.cache_resource(show_spinner=False)
def load_embeddings():
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'},  
        encode_kwargs={'normalize_embeddings': True}  
    )


@st.cache_resource(show_spinner=False)

def create_vector_store(_embeddings):
  
    loader = PyPDFLoader("FR_Y-9C.pdf") 

    docs = loader.load()
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,  
        chunk_overlap=150, 
        separators=["\n\n", "\n", ".", " "] 
    )
    final_documents = text_splitter.split_documents(docs[:12]) 
    
    return FAISS.from_documents(final_documents, _embeddings)


embeddings = load_embeddings()
vector_store = create_vector_store(embeddings)

st.title("Fin-Chat Demo")










@st.cache_resource
def load_llm():
    return ChatGroq(
        groq_api_key=os.environ['groq_api_key'],
        model_name="gemma2-9b-it",
        temperature=0.1  
    )

llm = load_llm()


@st.cache_resource
def create_retrieval_chain_wrapper(_llm, _retriever):
    prompt = ChatPromptTemplate.from_template("""
    Answer strictly using ONLY the context below. If unsure, say "I don't know".
    <context>
    {context}
    </context>
    Question: {input}
    """)
    
    document_chain = create_stuff_documents_chain(_llm, prompt)
    return create_retrieval_chain(_retriever, document_chain)

retriever = vector_store.as_retriever(search_kwargs={"k": 3})  
retrieval_chain = create_retrieval_chain_wrapper(llm, retriever)





prompt = st.text_input("Ask about the FR Y-9C report")

if prompt:
    start_time = time.perf_counter()
    
    with st.spinner("Analyzing documents , wait "):
        response = retrieval_chain.invoke({"input": prompt})
    
    st.success(f"Response time: {time.perf_counter() - start_time:.2f}s")
    st.write(response['answer'])
    
    with st.expander("Source Documents"):
        for i, doc in enumerate(response["context"]):
            st.caption(f"Document {i+1}:")
            st.text(doc.page_content[:500] + "...") 
            st.write("---")