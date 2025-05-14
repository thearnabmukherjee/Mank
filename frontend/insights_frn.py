
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
        st.subheader("📝Product Insights")
        
        # if insights_data and insights_data.get('labels'):
        if insights_data and insights_data.get('themes'):

            # Display summary
            st.markdown("### 📌Summary")
            st.markdown(insights_data.get('summary', 'No summary available'))
            


            # st.markdown("### 🧠 Thematic Label Breakdown")

            # for theme, items in insights_data["themes"].items():
            #     st.markdown(f"## 🔹 Theme: {theme}")
            #     for item in items:
            #         with st.expander(f"🏷️ {item['label']} ({item['count']} mentions)"):
            #             st.markdown("#### Insights")
            #             for action in item.get("actions", []):
            #                 reason = action.get("reason", "")
            #                 suggestion = action.get("action", "")
            #                 st.markdown(f"- **Reason:** _{reason}_\n  ➤ **Action:** _{suggestion}_")

            #             if item.get("sample_texts"):
            #                 st.markdown("#### Sample Text Excerpts")
            #                 for text in item["sample_texts"][:3]:
            #                     st.markdown(f"> *\"{text}\"*")

# Theme color mapping for visuals
            theme_colors = {
                "Clinical Performance": "#e6f0ff",
                "Marketing Effectiveness": "#e6ffe6",
                "Pricing Strategy": "#fff4e6",
                "Patient Engagement": "#f0f0f5",
                "Sales Strategy": "#f9f9f9",
                "Adoption Challenges": "#ffe6f2",
                "Operational Efficiency": "#f2ffe6",
                "Competitive Positioning": "#f0ffff",
                "Light Version Launch": "#f0e6ff",
                "Other": "#eeeeee"
            }

            st.markdown("### 🧠 Thematic Label Breakdown")

            for theme, items in insights_data["themes"].items():
                color = theme_colors.get(theme, "#f8f8f8")
                st.markdown(f"<div style='background-color:{color}; padding: 20px; border-radius: 12px; margin-bottom: 30px;'>", unsafe_allow_html=True)
                st.markdown(f"## 🧩 <u>{theme}</u>", unsafe_allow_html=True)

                for item in items:
                    st.markdown(f"<div style='background-color:white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin-top: 15px;'>", unsafe_allow_html=True)
                    st.markdown(f"### 🏷️ {item['label']} ({item['count']} mentions)")

                    # Insights
                    st.markdown("**🔍 Insights:**")
                    for reason in item.get("reasons", []):
                        st.markdown(f"- {reason}")

                    # Actions
                    st.markdown("**✅ Actions:**")
                    for act in item.get("actions", []):
                        st.markdown(f"-  _{act.get('action')}_")

                    # Samples
                    # if item.get("sample_texts"):
                    #     st.markdown("**💬 Sample Texts:**")
                    #     for txt in item["sample_texts"][:2]:
                    #         st.markdown(f"> {txt}")

                    st.markdown("</div>", unsafe_allow_html=True)

                st.markdown("</div>", unsafe_allow_html=True)

                st.markdown("""
                <style>
                    h3, h4, h5 {
                        color: #1c1c1c;
                    }
                    .markdown-text-container {
                        font-size: 0.94rem;
                        line-height: 1.6;
                    }
                </style>
                """, unsafe_allow_html=True)




if __name__ == "__main__":
    main()

