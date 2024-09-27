import streamlit as st

def main():
    st.title('Education Chatbot Project')

    st.markdown("""
        ## Welcome to our Education Chatbot Project!

        This project aims to revolutionize the way we learn and teach. Our chatbot uses the state-of-the-art RAG (Retrieval-Augmented Generation) technique to provide accurate and reliable information. 

        But that's not all! Our chatbot also supports students by supplying video resources to enhance their learning experience. 

        We believe in the power of community and collective knowledge. That's why we've integrated a feature that allows users to upload their own knowledge. This way, we can continuously grow and diversify our course offerings.

        This chatbot is powered by the UStage API. You can get free access to this API by registering at [https://console.upstage.ai/home](https://console.upstage.ai/home).

        We hope you enjoy using our chatbot as much as we enjoyed building it. Happy learning!
        """)

if __name__ == '__main__':
    main()