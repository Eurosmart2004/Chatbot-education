import streamlit as st
import zipfile
import os
import shutil
import threading
from tool import convert_video_to_csv, create_db


if __name__ == '__main__':
    
    # Initialize session state variables if they don't exist
    if 'uploaded_file' not in st.session_state:
        st.session_state['uploaded_file'] = None

    if 'upload_status' not in st.session_state:
        st.session_state['upload_status'] = False

    if 'error_file' not in st.session_state:
        st.session_state['error_file'] = False

    if 'check_structure' not in st.session_state:
        st.session_state['check_structure'] = False

    if 'course_name' not in st.session_state:
        st.session_state['course_name'] = None

    if 'progress' not in st.session_state:
        st.session_state['progress'] = 0

    if 'process_vid_db' not in st.session_state:
        st.session_state['process_vid_db'] = False

    if 'create_db' not in st.session_state:
        st.session_state['create_db'] = False

    # Function to process videos and create database
    def process_videos_and_db(course_name, folder_extract):
        progress_vid = st.progress(0, "Progress process video")
        for progress in convert_video_to_csv(course_name, folder_extract):
            st.session_state.progress = progress
            progress_vid.progress(progress,"Progress process video")

        with st.spinner("Creating database..."):
            st.session_state.create_db = True
            create_db(course_name, folder_extract)

        st.success("Database created successfully.")

        target_path = os.path.join('resources', course_name)
        if os.path.exists(target_path):
            shutil.rmtree(target_path)  # Delete the existing directory
        
        shutil.move(os.path.join(folder_extract, course_name), 'resources')  # Move the new directory
        st.session_state.process_vid_db = False
        
    st.title('Prepare Database')
    st.markdown("""Please upload a zip file containing the resource for course following this structure:\n
    ```
    course_name/
        week-1/
            abc.pdf
            vid.mp4
        week-2/
            ...
    ```
    """)

    # Upload zip file
    uploaded_file = st.file_uploader("Choose a file")
    if uploaded_file is not None and uploaded_file.type == 'application/x-zip-compressed' and uploaded_file != st.session_state.uploaded_file:
        st.session_state.uploaded_file = uploaded_file
        st.session_state.upload_status = True

    if st.session_state.uploaded_file:
        st.success("Zip file uploaded successfully.")

    # Check if the file is uploaded and the structure is correct

    if st.session_state.upload_status:
        st.write("Extracting files...")
        folder_extract = 'temp'

        if not st.session_state.check_structure:

            with zipfile.ZipFile(st.session_state.uploaded_file, 'r') as zip_ref:
                zip_ref.extractall(folder_extract)

            directories = [name for name in os.listdir(folder_extract) if os.path.isdir(os.path.join(folder_extract, name))]
            if len(directories) != 1:
                st.session_state.error_file = True
                st.error("The zip file should contain exactly one directory, which is the name of the course.")
            else:
                st.session_state.course_name = directories[0]

                missing_weeks = [f"week-{i}" for i in range(1, 12) if not os.path.exists(os.path.join(folder_extract, st.session_state.course_name, f"week-{i}"))]
                if missing_weeks:
                    st.session_state.error_file = True
                    st.error(f"The following weeks are missing from the course directory: {', '.join(missing_weeks)}")
                else:
                    st.session_state.check_structure = True

        if st.session_state.error_file:
            shutil.rmtree(os.path.join(folder_extract, st.session_state.course_name))
            st.session_state.upload_status = False
            st.session_state.check_structure = False
            st.session_state.error_file = False
            st.session_state.file_uploaded = None
        else:
            if not st.session_state.process_vid_db:
                if st.button("Start processing", disabled=st.session_state.process_vid_db):
                    st.write("Processing...")
                    st.session_state.process_vid_db = True
                    process_videos_and_db(st.session_state.course_name, folder_extract)

