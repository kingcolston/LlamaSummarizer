from flask import Flask, request, jsonify
from flask_cors import CORS
import json
from llamaapi import LlamaAPI
import re
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Access environment variables
api_key = os.getenv("API_KEY")

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'


@app.route('/summarize', methods=['POST'])
def summarize_transcript():
    # Initialize the SDK
    llama = LlamaAPI(api_key)
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No file selected for uploading'}), 400

    if file:
        try:
            prompt_to_send = sanitize_data(file)
            api_request_json = {
                "messages": [
                    {"role": "user", "content": prompt_to_send},
                ],
                "stream": False
            }

            # Execute the Request
            response = llama.run(api_request_json)
            response = response.json()
            print(response['choices'][0]['message']['content'])
            return response['choices'][0]['message']['content'], 200

        except:
            return 'An error has occurred with the API', 500


def sanitize_data(file):
    transcript = None
    if file.filename.endswith('.txt'):
        print('Text file detected')
        try:
            transcript = sanitize_txt_file(file)
        except:
            print('Weird text format detected. Going to try and summarize just the text..')
            transcript = file.read().decode('utf-8')
            return prompt_string(transcript)
    elif file.filename.endswith('.json'):
        print('JSON file detected')
        transcript = sanitize_json_file(file)
    else:
        print('Invalid file format')

    return prompt_string(transcript)


def sanitize_txt_file(file):
    transcript = file.read().decode('utf-8')
    transcript = transcript.splitlines()
    sanitized_data = []
    last_speaker = None
    for line in transcript:
        if line.find('-->') > 0 or 'WEBVTT' in line or re.match('^\d+$', line):
            continue
        line = line.strip()
        if not line:
            continue
        speaker, dialogue = line.split(":", 1)
        speaker = speaker.strip()
        dialogue = dialogue.strip()
        if len(sanitized_data) > 0 and speaker == last_speaker:
            last_entry = sanitized_data[-1]
            last_entry += f" {dialogue}"
            sanitized_data[-1] = last_entry
        else:
            sanitized_data.append(f"{speaker}: {dialogue}")
            last_speaker = speaker

    return sanitized_data


def sanitize_json_file(file):
    content = file.read().decode('utf-8')
    data = json.loads(content)
    transcript_list = data['result']['transcriptList']
    final_transcript = []
    for transcript in transcript_list:
        if len(final_transcript) == 0:
            text_added = f"{transcript['username']}: {transcript['text']}"
            final_transcript.append(text_added)
        else:
            last_entry = final_transcript[-1]
            if transcript['username'] in last_entry:
                last_entry += f" {transcript['text']}"
                final_transcript[-1] = last_entry
            else:
                text_added = f"{transcript['username']}: {transcript['text']}"
                final_transcript.append(text_added)

    return final_transcript


def prompt_string(transcript):
    transcript_concat = ''
    for line in transcript:
        transcript_concat += f"{line}\n"

    prompt = (f"Write a concise summary of the following text delimited by triple backquotes. Return your response in "
              f"bullet points which covers the key points of the text. The format of the text will be in the format "
              f"<NAME>:<MESSAGE_HERE>"
              f"\n\n```{transcript_concat}```\n\n")
    print(prompt)
    return prompt



if __name__ == '__main__':
    app.run(debug=True)
