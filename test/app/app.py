import streamlit as st
from model.DocumentProcessing import DocumentResource, DocumentResponse
from ai import chat

# Set Streamlit page config
st.set_page_config(page_title="Knowledge Retrieval Assistant", layout="wide")

# Custom CSS for better UI
st.markdown("""
    <style>
        .chat-container {
            max-width: 900px;
            margin: auto;
        }
        .document-container {
            border: 1px solid #ddd;
            padding: 10px;
            border-radius: 8px;
            background-color: #f9f9f9;
            margin-bottom: 10px;
        }
        .user-message {
            background-color: #dcf8c6;
            padding: 10px;
            border-radius: 10px;
            margin-bottom: 10px;
        }
        .assistant-message {
            background-color: #ebebeb;
            padding: 10px;
            border-radius: 10px;
            margin-bottom: 10px;
        }
    </style>
""", unsafe_allow_html=True)

# Sidebar with filter settings
with st.sidebar:
    st.header("🔍 Search Settings")
    confidence_threshold = st.slider("Confidence Threshold", 0.0, 1.0, 0.7)
    max_results = st.slider("Max Documents", 1, 10, 5)

# Main UI Title
st.title("📚 Knowledge Retrieval Assistant")

st.write("Ask me anything! This assistant retrieves relevant knowledge from indexed documents.")

# Initialize session state for chat history
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Display previous chat history
with st.container():
    for message in st.session_state.messages:
        with st.chat_message(message['role']):
            st.markdown(message['content'])

# Chat input
user_input = st.chat_input("Type your question here...")

if user_input:
    # Display the user's input in chat
    with st.chat_message("user"):
        st.markdown(f"**You:** {user_input}")

    # Store user message in session state
    st.session_state.messages.append({"role": "user", "content": f"**You:** {user_input}"})

    # Call knowledge retrieval function
    document_response = chat.get_qa_from_query(user_input)

    # Display the assistant's response
    with st.chat_message("assistant"):
        st.markdown(f"**Assistant:** {document_response.answer}")

    # Store assistant's response in session state
    st.session_state.messages.append({"role": "assistant", "content": f"**Assistant:** {document_response.answer}"})

    # Display retrieved documents
    if document_response.Documents:
        st.subheader("📄 Relevant Documents")
        for doc in document_response.Documents[:max_results]:
            with st.expander(f"📌 {doc.title} (Page {doc.pageNumber})", expanded=False):
                st.write(doc.content)
    else:
        st.info("No relevant documents found.")
