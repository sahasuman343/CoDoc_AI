import streamlit as st
import streamlit_mermaid as stmd

import requests
import time

# Backend URL
BACKEND_URL = "http://localhost:8000"  # Update this if your backend runs on a different URL/port

st.title("Codebase Documentation Maker")
st.write("Provide a GitHub repository link to generate AI-powered documentation and diagrams.")

# GitHub link input
github_link = st.text_input("Enter the GitHub repository URL")

# Options for analysis
include_documentation = st.checkbox("Include Documentation", value=True)
include_diagrams = st.checkbox("Include Diagrams", value=True)

# Submit button
if st.button("Start Analysis"):
    if not github_link:
        st.error("Please provide a valid GitHub repository URL.")
    else:
        # Prepare the request payload
        data = {
            "source": github_link,
            "input_type": "github_url",
            "include_documentation": include_documentation,
            "include_diagrams": include_diagrams,
            "max_files": 1000,
        }

        # Send the request to the backend
        st.info("Starting analysis...")
        try:
            response = requests.post(f"{BACKEND_URL}/analyze", json=data)
            if response.status_code == 200:
                analysis_id = response.json().get("analysis_id")
                st.success(f"Analysis started! Analysis ID: {analysis_id}")

                # Poll the backend for analysis status
                st.info("Checking analysis status...")
                while True:
                    status_response = requests.get(f"{BACKEND_URL}/analysis/{analysis_id}/status")
                    status_data = status_response.json()

                    if status_data["status"] == "completed":
                        st.success("Analysis completed successfully!")
                        result_response = requests.get(f"{BACKEND_URL}/analysis/{analysis_id}/result")
                        result_data = result_response.json()

                        # Display results
                        st.subheader("Project Overview")
                        st.write(result_data["project_overview"])

                        st.subheader("File Structure")
                        st.json(result_data["file_structure"])

                        if include_documentation:
                            st.subheader("File Documentation")
                            st.json(result_data["file_documentation"])

                        if include_diagrams:
                            st.subheader("Sequence Diagram")
                            # st.image(result_data["sequence_diagram"])
                            stmd.st_mermaid(result_data["sequence_diagram"])

                            st.subheader("Class Diagram")
                            # st.image(result_data["class_diagram"])
                            stmd.st_mermaid(result_data["class_diagram"])
                        break
                    elif status_data["status"] == "failed":
                        st.error(f"Analysis failed: {status_data.get('error', 'Unknown error')}")
                        break
                    else:
                        st.info(f"Progress: {status_data['progress']}% - {status_data['message']}")
                        time.sleep(5)
            else:
                st.error(f"Failed to start analysis: {response.text}")
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")