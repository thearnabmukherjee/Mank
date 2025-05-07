# import streamlit as st
# import requests
# from datetime import datetime

# # Configuration
# BACKEND_URL = "http://localhost:8000"

# def fetch_medicines():
#     response = requests.get(f"{BACKEND_URL}/medicines/")
#     return response.json() if response.status_code == 200 else []

# def fetch_labels(medicine_name):
#     response = requests.get(f"{BACKEND_URL}/medicines/{medicine_name}/labels")
#     return response.json() if response.status_code == 200 else []

# def generate_insights(medicine_name, label=None):
#     data = {"medicine_name": medicine_name}
#     if label:
#         data["label"] = label
#     return requests.post(f"{BACKEND_URL}/insights/generate", data=data)

# def fetch_insights(medicine_name=None, label=None):
#     params = {"limit": 10}
#     if medicine_name:
#         params["medicine_name"] = medicine_name
#     if label:
#         params["label"] = label
#     return requests.get(f"{BACKEND_URL}/insights/history", params=params)

# # Streamlit App
# def main():
#     st.title("Pharmaceutical Insights Dashboard")
    
#     # Sidebar filters
#     st.sidebar.header("Analysis Parameters")
#     medicine_name = st.sidebar.selectbox("Select Medicine", options=fetch_medicines())
    
#     labels_data = fetch_labels(medicine_name)
#     label_options = [None] + [label["label"] for label in labels_data]
#     selected_label = st.sidebar.selectbox(
#         "Filter by Label (Optional)",
#         options=label_options,
#         format_func=lambda x: "All Labels" if x is None else x
#     )
    
#     # Main content
#     if st.button("Generate New Insights"):
#         response = generate_insights(medicine_name, selected_label)
#         if response.status_code == 200:
#             st.success("Insight generation started! Check back soon.")
#         else:
#             st.error("Failed to start insight generation")
    
#     st.header("Historical Insights")
#     insights_response = fetch_insights(medicine_name, selected_label)
    
#     if insights_response.status_code == 200:
#         insights = insights_response.json()
#         if not insights:
#             st.info("No insights found for these filters.")
#         else:
#             for insight in insights:
#                 with st.expander(f"{insight['medicine_name']} - {insight.get('label', 'All Labels')} - {datetime.fromisoformat(insight['generated_at']).strftime('%Y-%m-%d %H:%M')}"):
#                     st.markdown("### Insights Summary")
#                     st.markdown(insight["insights"])
                    
#                     if st.button("View Details", key=f"details_{insight['_id']}"):
#                         st.json(insight["context"], expanded=False)
#     else:
#         st.error("Failed to fetch insights")

# if __name__ == "__main__":
#     main()






import streamlit as st
import requests
from datetime import datetime
import pandas as pd
import plotly.express as px

# Configuration
BACKEND_URL = "http://localhost:8000"

def fetch_medicines():
    """Fetch all available medicine names from backend"""
    try:
        response = requests.get(f"{BACKEND_URL}/medicines/")
        return response.json() if response.status_code == 200 else []
    except requests.exceptions.RequestException:
        return []

def fetch_medicine_labels(medicine_name):
    """Fetch all labels for a specific medicine"""
    try:
        response = requests.get(f"{BACKEND_URL}/medicines/{medicine_name}/labels")
        if response.status_code == 200:
            return response.json()
        return []
    except requests.exceptions.RequestException:
        return []

def fetch_medicine_insights(medicine_name):
    """Fetch comprehensive label insights for a medicine"""
    try:
        response = requests.get(f"{BACKEND_URL}/medicines/{medicine_name}/insights")
        return response.json() if response.status_code == 200 else None
    except requests.exceptions.RequestException:
        return None

def generate_insights(medicine_name, label=None):
    """Trigger insight generation"""
    try:
        data = {"medicine_name": medicine_name}
        if label:
            data["label"] = label
        response = requests.post(f"{BACKEND_URL}/insights/generate", data=data)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def fetch_insights_history(medicine_name=None, label=None, limit=10):
    """Fetch historical insights"""
    try:
        params = {"limit": limit}
        if medicine_name:
            params["medicine_name"] = medicine_name
        if label:
            params["label"] = label
        response = requests.get(f"{BACKEND_URL}/insights/history", params=params)
        return response.json() if response.status_code == 200 else []
    except requests.exceptions.RequestException:
        return []

def main():
    st.set_page_config(
        page_title="Pharma Insights Dashboard",
        page_icon="💊",
        layout="wide"
    )
    
    # Custom CSS
    # st.markdown("""
    # <style>
    #     .stButton>button {
    #         background-color: #4CAF50;
    #         color: white;
    #         font-weight: bold;
    #     }
    #     .st-expander {
    #         background-color: #f0f2f6;
    #         border-radius: 8px;
    #         padding: 10px;
    #     }
    #     .metric-card {
    #         background-color: white;
    #         border-radius: 8px;
    #         padding: 15px;
    #         box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    #         margin-bottom: 15px;
    #     }
    #     .label-card {
    #         background-color: white;
    #         border-radius: 8px;
    #         padding: 15px;
    #         box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    #         margin-bottom: 10px;
    #     }
    # </style>
    # """, unsafe_allow_html=True)

    # Add this to the custom CSS section
    st.markdown("""
    <style>
        .label-card {
            background-color: white;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 15px;
            min-height: 120px;
        }
        .label-card h3 {
            color: #2c3e50;
            border-bottom: 1px solid #eee;
            padding-bottom: 8px;
        }
        .label-card ul {
            margin-top: 8px;
            padding-left: 20px;
        }
    </style>
    """, unsafe_allow_html=True)

    st.title("💊 Pharmaceutical Insights Dashboard")
    st.markdown("Analyze business insights from medical transcripts")

    # Sidebar filters
    with st.sidebar:
        st.header("🔍 Filters")
        medicine_name = st.selectbox(
            "Select Medicine",
            options=fetch_medicines(),
            index=0,
            help="Select a medicine to analyze"
        )

        if medicine_name:
            labels_data = fetch_medicine_labels(medicine_name)
            label_options = [{"label": "All Labels", "value": None}]
            label_options.extend([{"label": lbl["label"], "value": lbl["label"]} for lbl in labels_data])
            selected_label = st.selectbox(
                "Filter by Label",
                options=label_options,
                format_func=lambda x: x["label"],
                index=0,
                help="Filter insights by specific label"
            )

            if st.button("🔄 Generate New Insights", help="Generate fresh insights for selected filters"):
                with st.spinner("Generating insights..."):
                    success = generate_insights(medicine_name, selected_label["value"] if selected_label["value"] else None)
                    if success:
                        st.success("Insight generation started! Check back soon.")
                    else:
                        st.error("Failed to start insight generation")

    if not medicine_name:
        st.warning("Please select a medicine to begin analysis")
        return

    # Main content
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("📊 Medicine Overview")
        
        # Fetch comprehensive insights
        insights_data = fetch_medicine_insights(medicine_name)
        
        if insights_data:
            # Metrics cards
            st.markdown(f"""
            <div class="metric-card">
                <h3>📝 Documents Analyzed</h3>
                <h2>{insights_data.get('document_count', 0)}</h2>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="metric-card">
                <h3>🏷️ Unique Labels</h3>
                <h2>{len(insights_data.get('labels', {}))}</h2>
            </div>
            """, unsafe_allow_html=True)
            
            # Label frequency chart
            if insights_data.get('labels'):
                labels_df = pd.DataFrame([
                    {"label": label, "count": data["count"]}
                    for label, data in insights_data["labels"].items()
                ])
                fig = px.bar(
                    labels_df.sort_values("count", ascending=False).head(10),
                    x="label",
                    y="count",
                    title="Top 10 Labels by Frequency"
                )
                fig.update_layout(height=300)
                st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("📝 Label Analysis")
        
        if insights_data and insights_data.get('labels'):
            # Display summary
            st.markdown("### 📌 Executive Summary")
            st.markdown(insights_data.get('summary', 'No summary available'))
            
            # Detailed label analysis
            st.markdown("### 🔍 Detailed Label Breakdown")
            for label, data in insights_data["labels"].items():
                with st.expander(f"🏷️ {label} (appears in {data['count']} documents)"):
                    st.markdown("#### Reasons for this label:")
                    for reason in data.get('reasons', []):
                        st.markdown(f"- {reason}")
                    
                    if data.get('sample_texts'):
                        st.markdown("#### Sample text excerpts:")
                        for text in data.get('sample_texts', [])[:3]:
                            st.markdown(f"> *\"{text}\"*")

    # Historical insights section
    st.subheader("🕰️ Historical Insights")
    insights_history = fetch_insights_history(
        medicine_name=medicine_name,
        label=selected_label["value"] if selected_label["value"] else None,
        limit=5
    )
    
    if insights_history:
        for insight in insights_history:
            with st.expander(
                f"📅 {datetime.fromisoformat(insight['generated_at']).strftime('%Y-%m-%d %H:%M')} | "
                f"{insight['medicine_name']} | "
                f"{insight.get('label', 'All Labels')}"
            ):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown("### Insights Summary")
                    st.markdown(insight.get('insights', 'No insights available'))
                with col2:
                    st.metric("Documents Analyzed", insight.get('document_count', 0))
                
                if st.button("View Detailed Context", key=f"context_{insight['_id']}"):
                    st.json(insight.get('context', {}), expanded=False)
    else:
        st.info("No historical insights found for the selected filters.")

    st.subheader("🕰️ Product Insights")
    insights_history = fetch_insights_history(
        medicine_name=medicine_name,
        label=selected_label["value"] if selected_label["value"] else None,
        limit=1  # Get only the latest insight
    )

    if insights_history:
        insight = insights_history[0]
        insight_text = insight.get('insights', '')
        
        # Parse the structured insight text
        sections = {
            "Feedback": "",
            "Competition": "",
            "Pricing": "",
            "MR Suggestions": "",
            "Additional Insights": ""
        }
        
        current_section = None
        for line in insight_text.split('\n'):
            line = line.strip()
            if line.startswith('**Feedback**'):
                current_section = "Feedback"
            elif line.startswith('## Competition'):
                current_section = "Competition"
            elif line.startswith('## Pricing'):
                current_section = "Pricing"
            elif line.startswith('## MR Suggestions'):
                current_section = "MR Suggestions"
            elif line.startswith('## Additional Insights'):
                current_section = "Additional Insights"
            elif current_section and line and not line.startswith('---'):
                sections[current_section] += line + '\n'
        
        # Display the parsed sections in cards
        cols = st.columns(2)
        with cols[0]:
            with st.container():
                st.markdown("### Feedback")
                st.markdown(f"""
                <div class="label-card">
                    {sections["Feedback"] or "No feedback available"}
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("### Competition")
                st.markdown(f"""
                <div class="label-card">
                    {sections["Competition"] or "No competition data available"}
                </div>
                """, unsafe_allow_html=True)
        
        with cols[1]:
            with st.container():
                st.markdown("### Pricing")
                st.markdown(f"""
                <div class="label-card">
                    {sections["Pricing"] or "No pricing data available"}
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("### MR Suggestions")
                st.markdown(f"""
                <div class="label-card">
                    {sections["MR Suggestions"] or "No MR suggestions available"}
                </div>
                """, unsafe_allow_html=True)
        
        if sections["Additional Insights"]:
            st.markdown("### Additional Insights")
            st.markdown(f"""
            <div class="label-card">
                {sections["Additional Insights"]}
            </div>
            """, unsafe_allow_html=True)
        
        if st.button("View Detailed Analysis", key=f"context_{insight['_id']}"):
            st.json(insight.get('context', {}), expanded=False)
    else:
        st.info("No insights found for the selected filters.")

if __name__ == "__main__":
    main()