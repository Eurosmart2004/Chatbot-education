class Video:
    def __init__(self, source, start, end):
        self.source = source
        self.start = start
        self.end = end

def process_resonse(response):
    import pandas as pd

    csv_file = pd.read_csv('convert.csv').set_index('local')
    if 'context' not in response:
        return response
    
    for context in response['context']:
        index = context.metadata['source'].find('resources')

        context.metadata['source'] = context.metadata['source'][index:]

        index = context.metadata['source'].find('.csv')
        if context.metadata['type'] == 'video':
            local_source = context.metadata['source'][0:index]
            
            if local_source in csv_file.index:
                context.metadata['source'] = csv_file.loc[local_source, 'url']

    return response


def extract_video(response):
    videos = []
    if 'context' not in response:
        return videos

    for context in response['context']:
        if context.metadata['type'] == 'video':
            source = context.metadata['source']
            start = context.metadata['Start']
            end = context.metadata['End']
            index = context.page_content.find('Text')
            text = context.page_content[index + len('Text: '):]

            # Check if there is already a video with this source
            for video in videos:
                if video['source'] == source:
                    # If there is, update the start and end times
                    if start == video['End']:
                        video['End'] = end
                        video['text'] += ' ' + text
                    if end == video['Start']:
                        video['Start'] = start
                        video['text'] = text + ' ' + video['text']
                    break
            else:
                # If there isn't, add a new video
                videos.append({
                    'source': source,
                    'Start': float(start),
                    'End': float(end),
                    'text': text
                })

    return videos[:2]


import re

def extract_weeks(user_query):
    # Define patterns for numerical and written week references
    week_patterns = [
        re.compile(r'week[-\s]*(\d+)', re.IGNORECASE),  # Matches 'week-2', 'week 2', 'week2'
        re.compile(r'week[-\s]*(one|two|three|four|five|six|seven|eight|nine|ten|eleven)', re.IGNORECASE)  # Matches 'week two', 'weekfive', 'week six'
    ]
    
    # Dictionary to convert written numbers to digits
    number_words = {
        'one': '1', 'two': '2', 'three': '3', 'four': '4', 'five': '5',
        'six': '6', 'seven': '7', 'eight': '8', 'nine': '9', 'ten': '10', 'eleven': '11'
    }
    
    weeks = []
    
    for pattern in week_patterns:
        matches = pattern.findall(user_query)
        for match in matches:
            # Check if the match is a digit or a word and normalize it
            if match.isdigit():
                week_number = match
            else:
                week_number = number_words.get(match.lower(), match)
            weeks.append(f'week-{week_number}')
    
    # Remove duplicates and filter out any incorrect matches
    weeks = list(set(weeks))
    weeks = [week for week in weeks if re.match(r'week-\d+', week)]
    
    return weeks if weeks else None



# def convert_video_to_csv(courseName, extract_folder='temp'):
#     import whisper
#     import os
#     import csv

#     model = whisper.load_model("base")
#     fileCount = 0
#     for i in range(1,12):
#         folder_path = f'{extract_folder}/{courseName}/week-{i}'
#         if os.path.exists(folder_path):
#             for filename in os.listdir(folder_path):
#                 if filename.endswith('.mp4'):
#                     fileCount += 1

#     if fileCount == 0:
#         yield 100
#         return

#     for i in range(1, 12):
#         # Construct the folder path for the current week
#         folder_path = f'{extract_folder}/{courseName}/week-{i}'
#         count = 0
#         # Check if the folder exists
#         if os.path.exists(folder_path):
#             # Loop over each file in the folder
#             for filename in os.listdir(folder_path):
#                 # Check if the file is a video (e.g., has a .mp4 extension)
#                 if filename.endswith('.mp4'):
#                     # Construct the full file path
#                     file_path = os.path.join(folder_path, filename)

#                     # Now you can do something with the video file
#                     print(f'Processing video file: {file_path}')
                    
#                     result = model.transcribe(file_path)
                    

#                     with open(f'{folder_path}/{filename}.csv', 'w', newline='') as f:
#                         # Create a CSV writer
#                         writer = csv.writer(f)

#                         # Write the header
#                         writer.writerow(['Start', 'End', 'Text'])

#                         # Write the data
#                         for segment in result['segments']:
#                             writer.writerow([segment['start'], segment['end'], segment['text']])
#                     count += 1
#                     yield count/fileCount
#                     print(f'Finish process video file: {file_path}')

# def create_db(courseName, extract_folder='temp'):
#     from langchain_community.document_loaders import PyMuPDFLoader
#     from langchain_community.document_loaders.csv_loader import CSVLoader
#     from langchain_chroma import Chroma
#     from langchain_text_splitters import RecursiveCharacterTextSplitter
#     from langchain_upstage import UpstageEmbeddings
#     from dotenv import load_dotenv
#     import os
#     import pandas as pd
#     load_dotenv()

#     UPSTAGE_API_KEY = os.getenv('UPSTAGE_API_KEY')
#     base_dir = f'{extract_folder}/{courseName}'

#     # Process CSV files
#     csv_doc = []
#     # Loop over each directory in the base directory
#     for week_dir in os.listdir(base_dir):
#         # Construct the full directory path
#         full_dir = os.path.join(base_dir, week_dir)

#         # Check if it's a directory
#         if os.path.isdir(full_dir):
#             # Loop over each file in the directory
#             for filename in os.listdir(full_dir):
#                 # Check if the file is a CSV file
#                 if filename.endswith('.csv'):
#                     # Construct the full file path
#                     file_path = os.path.join(full_dir, filename)

#                     # Load the CSV file
#                     loader = CSVLoader(file_path=file_path, metadata_columns=['Start', 'End'])
#                     data = loader.load()

#                     for d in data:
#                         index = d.metadata['source'].find(courseName)
#                         d.metadata['source'] = f"resources/{d.metadata['source'][index:]}"
#                         d.metadata['type'] = 'video'
#                         d.metadata['week'] = week_dir

#                     # Now you can do something with the data
#                     csv_doc.extend(data)

#     # Process PDF files
#     pdf_doc = []
#     # Loop over each directory in the base directory
#     for week_dir in os.listdir(base_dir):
#         # Construct the full directory path
#         full_dir = os.path.join(base_dir, week_dir)

#         # Check if it's a directory
#         if os.path.isdir(full_dir):
#             # Loop over each file in the directory
#             for filename in os.listdir(full_dir):
#                 # Check if the file is a CSV file
#                 if filename.endswith('.pdf'):
#                     # Construct the full file path
#                     file_path = os.path.join(full_dir, filename)

#                     # Load the CSV file
#                     loader = PyMuPDFLoader(file_path=file_path)
#                     data = loader.load()

#                     for d in data:
#                         index = d.metadata['source'].find(courseName)
#                         d.metadata['source'] = f"resources/{d.metadata['source'][index:]}"
#                         d.metadata['type'] = 'pdf'
#                         d.metadata['week'] = week_dir

#                     # Now you can do something with the data
#                     pdf_doc.extend(data)

#     # Combine the CSV and PDF documents
#     docs = csv_doc + pdf_doc
#     text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
#     splits = text_splitter.split_documents(docs)
#     embeddings = UpstageEmbeddings(
#         api_key=UPSTAGE_API_KEY,
#         model="solar-embedding-1-large-query"
#     )
#     # Define the maximum batch size
#     max_batch_size = 64

#     # Split the 'splits' list into smaller batches
#     batches = [splits[i:i + max_batch_size] for i in range(0, len(splits), max_batch_size)]

#     # Insert each batch into the Chroma database
#     for batch in batches:
#         vectorstore = Chroma.from_documents(documents=batch, embedding=embeddings, persist_directory=f'db/{courseName}')