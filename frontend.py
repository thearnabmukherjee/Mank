import streamlit as st
from datetime import datetime
import requests
import tempfile
import os
import pandas as pd
from bson.objectid import ObjectId
import io

# API configuration
API_BASE_URL = "http://localhost:8000"  # Update this if your API is hosted elsewhere

def insert_data(text, title=None, audio_file=None, medicine_name=None):
    print(f"Frontend values - text: {text}, title: {title}, medicine_name: {medicine_name}")  # Debug
    
    data = {
        "text": text,
        "title": title or "",
        "medicine_name": medicine_name  # Explicit empty string if None
    }
    
    files = {}
    if audio_file:
        files["audio_file"] = (audio_file.name, audio_file, "audio/wav")
    
    print(f"Data being sent: {data}")  # Debug
    
    response = requests.post(
        f"{API_BASE_URL}/documents/", 
        data=data,
        files=files if files else None
    )
    response.raise_for_status()
    return response.json()["id"]


def update_data(document_id, new_text, new_title=None, new_audio=None):
    data = {"text": new_text, "audio_action": "keep"}
    files = {}
    
    if new_title is not None:
        data["title"] = new_title
    
    if new_audio is not None:
        data["audio_action"] = "replace"
        files["audio_file"] = (new_audio.name, new_audio, "audio/wav")
    elif new_audio is False:
        data["audio_action"] = "remove"
    
    response = requests.put(
        f"{API_BASE_URL}/documents/{document_id}",
        data=data,
        files=files if files else None
    )
    response.raise_for_status()
    return response.json()["modified_count"]

def get_audio(document_id):
    response = requests.get(f"{API_BASE_URL}/documents/{document_id}/audio")
    if response.status_code == 404 and "No audio attached" in response.text:
        return None
    response.raise_for_status()
    return bytes.fromhex(response.json()["audio"])

def fetch_all_data():
    response = requests.get(f"{API_BASE_URL}/documents/")
    response.raise_for_status()
    data = response.json()
    
    # Add medicine_name to the response data if necessary
    for doc in data:
        doc["medicine_name"] = doc.get("medicine_name", "Not Provided")  # Add fallback if missing
    
    return data


def fetch_one_data(document_id):
    response = requests.get(f"{API_BASE_URL}/documents/{document_id}")
    response.raise_for_status()
    return response.json()

def delete_data(document_id):
    response = requests.delete(f"{API_BASE_URL}/documents/{document_id}")
    response.raise_for_status()
    return response.json()["deleted_count"]

def extract_labels(document_id):
    response = requests.post(f"{API_BASE_URL}/documents/{document_id}/extract-labels")
    response.raise_for_status()
    return response.json()

def get_labels(document_id):
    response = requests.get(f"{API_BASE_URL}/documents/{document_id}/labels")
    response.raise_for_status()
    return response.json()

def fetch_documents_by_label(label: str):
    response = requests.get(f"{API_BASE_URL}/documents/by-label/{label}")
    response.raise_for_status()
    return response.json()

# Streamlit UI
def main():
    st.title("🎙️ Audio + Text Manager")
    st.caption("Manage text and audio documents with AI-powered label extraction")

    # Initialize session state
    if "selected_doc_id" not in st.session_state:
        st.session_state.selected_doc_id = None
    if "menu_choice" not in st.session_state:
        st.session_state.menu_choice = "View Documents"

    # Sidebar menu
    menu = ["View Documents", "View Labels", "Visuals", "Create Document", "Update Document", "Delete Document"]
    menu_choice = st.sidebar.selectbox(
        "Menu",
        menu,
        index=menu.index(st.session_state.menu_choice))
    
    # Update menu choice in session state
    if menu_choice != st.session_state.menu_choice:
        st.session_state.menu_choice = menu_choice
        if menu_choice != "Visuals":
            st.session_state.selected_doc_id = None
        st.rerun()

    choice = st.session_state.menu_choice

    if choice == "View Documents":
        st.subheader("Document Overview")
        try:
            documents = fetch_all_data()
            
            if not documents:
                st.info("No documents found in the database")
            else:
                # Prepare data for the table
                table_data = []
                for idx, doc in enumerate(documents, 1):
                    table_data.append({
                        "S.No": idx,
                        "ID": doc["_id"],
                        "Title": doc.get("title", "Untitled"),
                        "Has Audio": "✅" if doc.get("has_audio", False) else "❌",
                        "Labels": ", ".join(doc.get("labels", [])) if doc.get("labels") else "None",
                        "Last Updated": datetime.fromisoformat(doc["updated_at"]).strftime("%Y-%m-%d %H:%M")
                    })
                
                # Custom CSS for the table
                st.markdown("""
                    <style>
                        .stButton>button {
                            padding: 0.25rem 0.5rem;
                            font-size: 0.8rem;
                        }
                        .table-container {
                            margin-top: 1rem;
                        }
                        .header-row {
                            font-weight: bold;
                            border-bottom: 2px solid #ddd;
                        }
                        .data-row {
                            border-bottom: 1px solid #eee;
                        }
                        .label-badge {
                            display: inline-block;
                            padding: 0.2rem 0.4rem;
                            background-color: #e0f2fe;
                            border-radius: 0.5rem;
                            font-size: 0.8rem;
                            margin: 0.1rem;
                        }
                    </style>
                """, unsafe_allow_html=True)
                
                # Render table
                with st.container():
                    cols = st.columns([1, 3, 4, 2, 3, 3, 2])
                    headers = ["S.No", "ID", "Title", "Audio", "Labels", "Updated", "Action"]
                    for col, header in zip(cols, headers):
                        col.markdown(f"<div class='header-row'>{header}</div>", unsafe_allow_html=True)
                
                    for row in table_data:
                        with st.container():
                            cols = st.columns([1, 3, 4, 2, 3, 3, 2])
                            cols[0].write(row["S.No"])
                            cols[1].write(row["ID"])
                            cols[2].write(row["Title"])
                            cols[3].write(row["Has Audio"])
                            
                            # Format labels with badges
                            if row["Labels"] != "None":
                                labels_html = "<div>"
                                for label in row["Labels"].split(", "):
                                    labels_html += f"<span class='label-badge'>{label}</span>"
                                labels_html += "</div>"
                                cols[4].markdown(labels_html, unsafe_allow_html=True)
                            else:
                                cols[4].write("None")
                                
                            cols[5].write(row["Last Updated"])
                            if cols[6].button("View", key=f"view_{row['ID']}"):
                                st.session_state.selected_doc_id = row["ID"]
                                st.session_state.menu_choice = "Visuals"
                                st.rerun()
                
        except Exception as e:
            st.error(f"Failed to fetch documents: {str(e)}")

    elif choice == "View Labels":
        st.subheader("📋 All Extracted Labels")
        
        try:
            documents = fetch_all_data()
            
            if not documents:
                st.info("No documents found in the database")
            else:
                # Create a dictionary to group documents by label
                label_dict = {}
                
                for doc in documents:
                    if "labels" in doc and doc["labels"]:
                        for label in doc["labels"]:
                            if label not in label_dict:
                                label_dict[label] = []
                            label_dict[label].append({
                                "id": doc["_id"],
                                "title": doc.get("title", "Untitled"),
                                "text_preview": doc["text"][:100] + ("..." if len(doc["text"]) > 100 else ""),
                                "has_audio": doc.get("has_audio", False),
                                "updated_at": datetime.fromisoformat(doc["updated_at"]).strftime("%Y-%m-%d")
                            })
                
                if not label_dict:
                    st.info("No labels have been extracted yet. Create documents and extract labels first.")
                else:
                    # Sort labels alphabetically
                    sorted_labels = sorted(label_dict.keys())
                    
                    # Create tabs for different views
                    tab1, tab2 = st.tabs(["Label Cloud", "Detailed View"])
                    
                    with tab1:
                        st.markdown("### Label Cloud")
                        st.caption("Visual overview of all extracted labels")
                        
                        # Create a tag cloud
                        tags_html = """
                        <div style="
                            display: flex;
                            flex-wrap: wrap;
                            gap: 0.5rem;
                            margin: 1rem 0;
                        ">
                        """
                        
                        for label in sorted_labels:
                            count = len(label_dict[label])
                            # Vary size based on document count
                            size = 14 + min(count, 10) * 2
                            color_intensity = min(200 + count * 20, 900)
                            tags_html += f"""
                            <span style="
                                font-size: {size}px;
                                padding: 0.5rem 1rem;
                                background-color: #f0f9ff;
                                color: #0369a1;
                                border-radius: 1rem;
                                display: inline-block;
                                margin: 0.25rem;
                                border: 1px solid #bae6fd;
                                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                                cursor: pointer;
                            ">
                                {label} <small>({count})</small>
                            </span>
                            """
                        
                        tags_html += "</div>"
                        st.markdown(tags_html, unsafe_allow_html=True)
                        st.caption("Click any label in the Detailed View tab to see associated documents")
                    
                    with tab2:
                        st.markdown("### Detailed Label View")
                        st.caption("Browse documents by their labels")
                        
                        # Search/filter functionality
                        search_term = st.text_input("Search labels", "")
                        
                        # Create expandable sections for each label
                        for label in sorted_labels:
                            if search_term.lower() not in label.lower():
                                continue
                                
                            with st.expander(f"🔖 {label} ({len(label_dict[label])} documents)", expanded=False):
                                for doc in label_dict[label]:
                                    with st.container():
                                        col1, col2, col3 = st.columns([1, 4, 1])
                                        with col1:
                                            if st.button("View", key=f"view_{doc['id']}"):
                                                st.session_state.selected_doc_id = doc["id"]
                                                st.session_state.menu_choice = "Visuals"
                                                st.rerun()
                                        with col2:
                                            st.markdown(f"**{doc['title']}**")
                                            st.caption(doc["text_preview"])
                                            st.caption(f"Updated: {doc['updated_at']}")
                                        with col3:
                                            st.markdown("🎧" if doc["has_audio"] else "")
        
        except Exception as e:
            st.error(f"Failed to fetch documents: {str(e)}")

    elif choice == "Visuals":
        st.subheader("Document Visuals")
        
        if not st.session_state.selected_doc_id:
            st.info("Please select a document from View Documents to see details")
            if st.button("Back to View Documents"):
                st.session_state.menu_choice = "View Documents"
                st.rerun()
        else:
            try:
                selected_id = st.session_state.selected_doc_id
                doc = fetch_one_data(selected_id)
                
                if doc:
                    with st.container():
                        # Document metadata (including medicine_name)
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown(f"### {doc.get('title', 'Untitled Document')}")
                            st.markdown(f"**Medicine Name:** {doc.get('medicine_name', 'Not Provided')}")  # Display medicine_name
                        with col2:
                            if st.button("← Back to All Documents"):
                                st.session_state.menu_choice = "View Documents"
                                st.session_state.selected_doc_id = None
                                st.rerun()
        
        # Other document content...

                        
                        st.divider()
                        
                        # Basic info columns
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown(f"**ID:** `{doc['_id']}`")
                            st.markdown(f"**Created:** {datetime.fromisoformat(doc['created_at']).strftime('%Y-%m-%d %H:%M')}")
                        with col2:
                            st.markdown(f"**Last Updated:** {datetime.fromisoformat(doc['updated_at']).strftime('%Y-%m-%d %H:%M')}")
                            st.markdown(f"**Has Audio:** {'✅' if doc.get('has_audio', False) else '❌'}")
                        
                        st.divider()
                        
                        # Content section
                        st.markdown("### Content")
                        st.text_area(
                            "Transcript", 
                            value=doc["text"], 
                            height=300, 
                            disabled=True,
                            label_visibility="collapsed"
                        )
                        
                        # Audio section
                        if doc.get("has_audio", False):
                            st.divider()
                            st.markdown("### Audio Attachment")
                            audio_data = get_audio(doc["_id"])
                            if audio_data:
                                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                                    tmp.write(audio_data)
                                    tmp_path = tmp.name
                                audio_bytes = open(tmp_path, 'rb').read()
                                st.audio(audio_bytes, format='audio/wav')
                                os.unlink(tmp_path)
                            else:
                                st.warning("Audio file could not be loaded")
                        
                        # Labels section
                        st.divider()
                        st.markdown("### Analysis Labels")
                        
                        if "labels" in doc and doc["labels"]:
                            cols = st.columns(3)
                            for idx, label in enumerate(doc["labels"]):
                                with cols[idx % 3]:
                                    st.markdown(
                                        f"""
                                        <div style='
                                            padding: 0.5rem;
                                            margin: 0.25rem 0;
                                            background-color: #f0f2f6;
                                            border-radius: 0.5rem;
                                            border-left: 4px solid #4e79a7;
                                        '>
                                            <strong>{label}</strong>
                                        </div>
                                        """,
                                        unsafe_allow_html=True
                                    )
                        else:
                            st.info("No labels generated yet")
                        
                        # Label extraction button
                        if st.button("✨ Extract Labels Using AI", type="primary"):
                            with st.spinner("Analyzing content and extracting labels..."):
                                try:
                                    extract_labels(selected_id)
                                    st.success("Label extraction started! Refresh in a few moments to see results.")
                                except Exception as e:
                                    st.error(f"Failed to start label extraction: {str(e)}")
                        
                        st.divider()
                        
                        # Document actions
                        st.markdown("### Document Actions")
                        action_cols = st.columns(3)
                        with action_cols[0]:
                            if st.button("Edit This Document"):
                                st.session_state.menu_choice = "Update Document"
                                st.rerun()
                        with action_cols[1]:
                            if st.button("View in Documents List"):
                                st.session_state.menu_choice = "View Documents"
                                st.rerun()
                        with action_cols[2]:
                            if st.button("Delete This Document", type="secondary"):
                                st.session_state.menu_choice = "Delete Document"
                                st.rerun()
                        
            except Exception as e:
                st.error(f"Failed to fetch document: {str(e)}")
                if st.button("Back to View Documents"):
                    st.session_state.menu_choice = "View Documents"
                    st.session_state.selected_doc_id = None
                    st.rerun()

    elif choice == "Create Document":
        st.subheader("Add New Document")
        with st.form("create_form"):
            title = st.text_input("Title (optional)")
            text = st.text_area("Text Content*", height=200)
            medicine_name = st.text_input("Medicine Name (optional)")
            audio_file = st.file_uploader("Upload Audio (optional)", type=["wav", "mp3", "ogg"])
            submitted = st.form_submit_button("Save Document")
            
            if submitted:
                if text.strip():
                    try:
                        doc_id = insert_data(
                            text=text.strip(),
                            title=title.strip() if title else None,
                            medicine_name=medicine_name.strip() if medicine_name else None,
                            audio_file=audio_file
                        )
                        st.success(f"Document saved with ID: `{doc_id}`")
                        st.balloons()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to create document: {str(e)}")
                else:
                    st.warning("Text content is required")  


    elif choice == "Update Document":
        st.subheader("Update Document")
        try:
            documents = fetch_all_data()
            
            if not documents:
                st.info("No documents available to update")
            else:
                selected_id = st.selectbox(
                    "Select document to update",
                    options=[doc["_id"] for doc in documents],
                    format_func=lambda x: f"{next(d.get('title', 'Untitled') for d in documents if d['_id'] == x)} (ID: {x})"
                )
                
                selected_doc = fetch_one_data(selected_id)
                
                if selected_doc:
                    with st.form("update_form"):
                        new_title = st.text_input(
                            "Title", 
                            value=selected_doc.get("title", "")
                        )
                        new_text = st.text_area(
                            "Content", 
                            value=selected_doc["text"],
                            height=300
                        )
                        
                        st.markdown("**Audio Update**")
                        audio_option = st.radio(
                            "Audio action:",
                            ["Keep current", "Replace", "Remove"],
                            index=0
                        )
                        
                        new_audio = None
                        if audio_option == "Replace":
                            new_audio = st.file_uploader("Upload new audio", type=["wav", "mp3", "ogg"])
                        elif audio_option == "Remove":
                            new_audio = False
                        
                        submitted = st.form_submit_button("Update Document")
                        
                        if submitted:
                            if new_text.strip():
                                try:
                                    count = update_data(
                                        selected_id,
                                        new_text.strip(),
                                        new_title.strip() if new_title else None,
                                        new_audio
                                    )
                                    if count > 0:
                                        st.success("Document updated successfully!")
                                        st.rerun()
                                    else:
                                        st.warning("No changes detected")
                                except Exception as e:
                                    st.error(f"Failed to update document: {str(e)}")
                            else:
                                st.warning("Text content cannot be empty")
        except Exception as e:
            st.error(f"Failed to fetch documents: {str(e)}")

    elif choice == "Delete Document":
        st.subheader("Delete Document")
        try:
            documents = fetch_all_data()
            
            if not documents:
                st.info("No documents available to delete")
            else:
                selected_id = st.selectbox(
                    "Select document to delete",
                    options=[doc["_id"] for doc in documents],
                    format_func=lambda x: f"{next(d.get('title', 'Untitled') for d in documents if d['_id'] == x)} (ID: {x})"
                )
                
                selected_doc = fetch_one_data(selected_id)
                
                if selected_doc:
                    st.warning("⚠️ This action cannot be undone!")
                    st.write("**Title:**", selected_doc.get("title", "Untitled"))
                    st.write("**Content preview:**", selected_doc["text"][:200] + ("..." if len(selected_doc["text"]) > 200 else ""))
                    
                    if selected_doc.get("has_audio", False):
                        st.write("**Has audio attachment**")
                    
                    if st.button("Confirm Permanent Delete"):
                        try:
                            count = delete_data(selected_id)
                            if count > 0:
                                st.success("Document deleted successfully!")
                                st.rerun()
                            else:
                                st.error("Failed to delete document")
                        except Exception as e:
                            st.error(f"Failed to delete document: {str(e)}")
        except Exception as e:
            st.error(f"Failed to fetch documents: {str(e)}")

if __name__ == "__main__":
    main()