import streamlit as st
import requests
import time
from typing import List, Dict, Any
from datetime import datetime

# API configuration
API_BASE_URL = "http://localhost:8001"  # Update this if your API is hosted elsewhere
# API_BASE_URL = "http://localhost:8000"
# Helper functions for API calls
def start_bulk_label_extraction():
    response = requests.post(f"{API_BASE_URL}/bulk-extract-labels/")
    response.raise_for_status()
    return response.json()

def get_bulk_extract_status():
    response = requests.get(f"{API_BASE_URL}/bulk-extract-labels/status")
    response.raise_for_status()
    return response.json()

def get_all_labels():
    response = requests.get(f"{API_BASE_URL}/labels/all")
    response.raise_for_status()
    return response.json()

def get_categorized_labels():
    response = requests.get(f"{API_BASE_URL}/labels/categorized")
    response.raise_for_status()
    return response.json()

# Streamlit UI
def main():
    st.title("💊 Medicine-Focused Label Analysis")
    st.caption("Generate and categorize labels specifically for medicines")

    # Initialize session state
    if "extraction_started" not in st.session_state:
        st.session_state.extraction_started = False
    if "last_status" not in st.session_state:
        st.session_state.last_status = None

    # Section 1: Bulk Label Extraction
    st.header("1. Extract Medicine-Related Labels")
    
    if st.button("💊 Start Medicine Label Extraction", type="primary"):
        with st.spinner("Starting medicine-focused label extraction..."):
            try:
                result = start_bulk_label_extraction()
                st.session_state.extraction_started = True
                st.session_state.last_status = result
                st.success("Medicine label extraction started successfully!")
            except Exception as e:
                st.error(f"Failed to start extraction: {str(e)}")

    if st.session_state.extraction_started:
        st.markdown("### Extraction Progress")
        
        # Create a progress container that we'll update
        progress_container = st.empty()
        status_container = st.empty()
        
        # Check status periodically
        while True:
            try:
                status = get_bulk_extract_status()
                st.session_state.last_status = status
                
                # Update progress bar
                progress = status["processed_documents"] / max(1, status["total_documents"])
                progress_container.progress(progress)
                
                # Update status text
                status_text = f"""
                **Status:** {status["status"].upper()}
                
                - Processed: {status["processed_documents"]} / {status["total_documents"]} documents
                - Medicine labels generated: {status["labels_generated"]}
                """
                status_container.markdown(status_text)
                
                if status["status"] == "complete":
                    st.balloons()
                    break
                
                time.sleep(2)  # Check every 2 seconds
                
            except Exception as e:
                status_container.error(f"Error checking status: {str(e)}")
                break

    # Section 2: View All Medicine Labels
    st.header("2. View All Medicine Labels")
    
    if st.button("🔄 Refresh Labels List"):
        st.rerun()
    
    try:
        labels = get_all_labels()
        
        if not labels:
            st.info("No medicine labels extracted yet. Run extraction first.")
        else:
            st.markdown(f"**Total Medicine Labels Extracted:** {len(labels)}")
            
            # Display labels in a scrollable container
            with st.expander("View All Medicine Labels", expanded=True):
                for label in labels:
                    st.markdown(
                        f"""
                        <div style='
                            padding: 0.75rem;
                            margin: 0.5rem 0;
                            background-color: #f0f9ff;
                            border-radius: 0.5rem;
                            border-left: 4px solid #3b82f6;
                        '>
                            💊 <strong>{label}</strong>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
    except Exception as e:
        st.error(f"Failed to fetch labels: {str(e)}")

    # Section 3: Categorized by Medicine
    st.header("3. View Categorized by Medicine")
    
    if st.button("🧪 Categorize by Medicine", type="secondary"):
        with st.spinner("Analyzing labels and categorizing by medicine..."):
            try:
                categorized = get_categorized_labels()
                
                if not categorized or not categorized.get("medicine_categories"):
                    st.warning("No medicine categories could be generated")
                else:
                    for category in categorized["medicine_categories"]:
                        # Determine color based on feedback type
                        color_map = {
                            "positive": "#10b981",
                            "negative": "#ef4444",
                            "neutral": "#64748b",
                            "comparison": "#8b5cf6",
                            "default": "#3b82f6"
                        }
                        border_color = color_map.get(
                            category.feedback_type.lower(), 
                            color_map["default"]
                        )
                        
                        with st.expander(
                            f"📦 {category.medicine_name} ({len(category.related_labels)} labels) - "
                            f"Feedback: {category.feedback_type.capitalize()}",
                            expanded=True
                        ):
                            for label in category.related_labels:
                                st.markdown(
                                    f"""
                                    <div style='
                                        padding: 0.75rem;
                                        margin: 0.5rem 0;
                                        background-color: #f8fafc;
                                        border-radius: 0.5rem;
                                        border-left: 4px solid {border_color};
                                    '>
                                        {label}
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )
            except Exception as e:
                st.error(f"Failed to categorize labels: {str(e)}")

if __name__ == "__main__":
    main()




# import streamlit as st
# import requests
# import time
# from typing import List, Dict, Any
# from datetime import datetime

# # API configuration
# API_BASE_URL = "http://localhost:8000"  # Update this if your API is hosted elsewhere

# # Helper functions for API calls
# def start_bulk_label_extraction():
#     response = requests.post(f"{API_BASE_URL}/bulk-extract-labels/")
#     response.raise_for_status()
#     return response.json()

# def get_bulk_extract_status():
#     response = requests.get(f"{API_BASE_URL}/bulk-extract-labels/status")
#     response.raise_for_status()
#     return response.json()

# def get_all_labels():
#     response = requests.get(f"{API_BASE_URL}/labels/all")
#     response.raise_for_status()
#     return response.json()

# def get_categorized_labels():
#     response = requests.get(f"{API_BASE_URL}/labels/categorized")
#     response.raise_for_status()
#     return response.json()

# # Streamlit UI
# def main():
#     st.title("💊 Medicine-Focused Label Analysis")
#     st.caption("Generate and categorize labels specifically for medicines")

#     # Initialize session state
#     if "extraction_started" not in st.session_state:
#         st.session_state.extraction_started = False
#     if "last_status" not in st.session_state:
#         st.session_state.last_status = None

#     # Section 1: Bulk Label Extraction
#     st.header("1. Extract Medicine-Related Labels")
    
#     if st.button("💊 Start Medicine Label Extraction", type="primary"):
#         with st.spinner("Starting medicine-focused label extraction..."):
#             try:
#                 result = start_bulk_label_extraction()
#                 st.session_state.extraction_started = True
#                 st.session_state.last_status = result
#                 st.success("Medicine label extraction started successfully!")
#             except Exception as e:
#                 st.error(f"Failed to start extraction: {str(e)}")

#     if st.session_state.extraction_started:
#         st.markdown("### Extraction Progress")
        
#         # Create a progress container that we'll update
#         progress_container = st.empty()
#         status_container = st.empty()
        
#         # Check status periodically
#         while True:
#             try:
#                 status = get_bulk_extract_status()
#                 st.session_state.last_status = status
                
#                 # Update progress bar
#                 progress = status["processed_documents"] / max(1, status["total_documents"])
#                 progress_container.progress(progress)
                
#                 # Update status text
#                 status_text = f"""
#                 **Status:** {status["status"].upper()}
                
#                 - Processed: {status["processed_documents"]} / {status["total_documents"]} documents
#                 - Medicine labels generated: {status["labels_generated"]}
#                 """
#                 status_container.markdown(status_text)
                
#                 if status["status"] == "complete":
#                     st.balloons()
#                     break
                
#                 time.sleep(2)  # Check every 2 seconds
                
#             except Exception as e:
#                 status_container.error(f"Error checking status: {str(e)}")
#                 break

#     # Section 2: View All Medicine Labels
#     st.header("2. View All Medicine Labels")
    
#     if st.button("🔄 Refresh Labels List"):
#         st.rerun()
    
#     try:
#         labels = get_all_labels()
        
#         if not labels:
#             st.info("No medicine labels extracted yet. Run extraction first.")
#         else:
#             st.markdown(f"**Total Medicine Labels Extracted:** {len(labels)}")
            
#             # Display labels in a scrollable container
#             with st.expander("View All Medicine Labels", expanded=True):
#                 for label in labels:
#                     st.markdown(
#                         f"""
#                         <div style='
#                             padding: 0.75rem;
#                             margin: 0.5rem 0;
#                             background-color: #f0f9ff;
#                             border-radius: 0.5rem;
#                             border-left: 4px solid #3b82f6;
#                         '>
#                             💊 <strong>{label}</strong>
#                         </div>
#                         """,
#                         unsafe_allow_html=True
#                     )
#     except Exception as e:
#         st.error(f"Failed to fetch labels: {str(e)}")

#     # Section 3: Categorized by Medicine
#     st.header("3. View Categorized by Medicine")
    
#     if st.button("🧪 Categorize by Medicine", type="secondary"):
#         with st.spinner("Analyzing labels and categorizing by medicine..."):
#             try:
#                 categorized = get_categorized_labels()
                
#                 if not categorized or not categorized.get("medicine_categories"):
#                     st.warning("No medicine categories could be generated")
#                 else:
#                     for category in categorized["medicine_categories"]:
#                         # Determine color based on feedback type
#                         color_map = {
#                             "positive": "#10b981",
#                             "negative": "#ef4444",
#                             "neutral": "#64748b",
#                             "comparison": "#8b5cf6",
#                             "default": "#3b82f6"
#                         }
#                         border_color = color_map.get(
#                             category.feedback_type.lower(), 
#                             color_map["default"]
#                         )
                        
#                         with st.expander(
#                             f"📦 {category.medicine_name} ({len(category.related_labels)} labels) - "
#                             f"Feedback: {category.feedback_type.capitalize()}",
#                             expanded=True
#                         ):
#                             for label in category.related_labels:
#                                 st.markdown(
#                                     f"""
#                                     <div style='
#                                         padding: 0.75rem;
#                                         margin: 0.5rem 0;
#                                         background-color: #f8fafc;
#                                         border-radius: 0.5rem;
#                                         border-left: 4px solid {border_color};
#                                     '>
#                                         {label}
#                                     </div>
#                                     """,
#                                     unsafe_allow_html=True
#                                 )
#             except Exception as e:
#                 st.error(f"Failed to categorize labels: {str(e)}")

# if __name__ == "__main__":
#     main()