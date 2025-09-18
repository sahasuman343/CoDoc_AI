import streamlit_mermaid as stmd
import streamlit as st

code = """
graph TD
    A --> B
    B --> C
    C --> D
"""
stmd.st_mermaid(code)