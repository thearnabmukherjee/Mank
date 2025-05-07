import streamlit as st

pages = {
    "Transcript Processing": [
        st.Page("Frontend.py", title="Enter Transcripts"),
        # st.Page("manage_account.py", title="Manage your account"),
    ],
    "Labels": [
        st.Page("visual_frn.py", title="Data Visuals"),
        st.Page("insights_frn.py", title="Insights"),
        st.Page("chats_frn.py", title="Chat"),
        st.Page("Dummy.py", title="Dummy Chat"),
        # st.Page("trial.py", title="Try it out"),
    ],
}

pg = st.navigation(pages)
pg.run()