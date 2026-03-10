import streamlit as st
from utils.config_manager import load_config, save_config

def show():

    st.title("System Settings")

    config = load_config()

    api_key = st.text_input(
        "Gemini API Key",
        value=config.get("gemini_api_key",""),
        type="password"
    )

    model = st.text_input(
        "Gemini Model",
        value=config.get("model","gemini-pro")
    )

    if st.button("Save Settings"):

        config["gemini_api_key"] = api_key
        config["model"] = model

        save_config(config)

        st.success("Settings Saved Successfully")