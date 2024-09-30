from flask import Flask, request, jsonify
from flask_cors import CORS
import urllib.request
import json
import openai
import os
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드. 코드는 저한테 물어보세용
load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/translation": {"origins": "http://localhost:3000"}})

# 환경 변수에서 API 키 로드
client_id = os.getenv("NAVER_CLIENT_ID")
client_secret = os.getenv("NAVER_CLIENT_SECRET")
openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route('/translation', methods=['POST'])
def translate():
    try:
        req_data = request.get_json()
        text_to_translate = req_data.get('text')
        source_lang = req_data.get('source', 'ko')
        target_lang = req_data.get('target', 'en')

        if not text_to_translate:
            return jsonify({'error': 'Text to translate is required.'}), 400

        # Papago API request 데이터 생성
        data = {
            'source': source_lang,
            'target': target_lang,
            'text': text_to_translate
        }

        url = "https://naveropenapi.apigw.ntruss.com/nmt/v1/translation"
        headers = {
            "X-NCP-APIGW-API-KEY-ID": client_id,
            "X-NCP-APIGW-API-KEY": client_secret,
            "Content-Type": "application/json"
        }

        # Papago API response 데이터 처리. 번역 내역 바로 처리합니다.
        data_encoded = json.dumps(data).encode('utf-8')
        api_request = urllib.request.Request(url, data=data_encoded, headers=headers)

        with urllib.request.urlopen(api_request) as response:
            rescode = response.getcode()
            response_body = response.read().decode('utf-8')
            if rescode == 200:
                result = json.loads(response_body)
                translated_text = result["message"]["result"]["translatedText"]

                # OpenAI API를 사용해 프롬프트 생성. 현재 딱히 화풍이 일치되지는 않는것같음..
                prompt = f"User's Diary: \"{translated_text}\". Please convert this diary to a prompt specified in the style of a cute and playful children's picture diary, with simple crayon or colored pencil drawings, and a warm and whimsical feeling. This image should feel like it was drawn by a child."

                gpt_response = openai.ChatCompletion.create(
                    model="gpt-4-turbo",
                    messages=[
                        {"role": "system", 
                         "content": "You are an assistant that helps generate image prompts."},
                        {"role": "user", 
                         "content": prompt}
                    ]
                )

                assistant_response = gpt_response['choices'][0]['message']['content']
                if "The prompt is:" in assistant_response:
                    image_prompt = assistant_response.split("The prompt is:")[1].strip()
                else:
                    image_prompt = assistant_response.strip()

                # DALL-E 이미지 생성 요청
                image_response = openai.Image.create(
                    prompt=image_prompt,
                    n=1,
                    size="1024x1024"
                )

                image_url = image_response['data'][0]['url']
                return jsonify({'translated_text': translated_text, 'image_prompt': image_prompt, 'image_url': image_url})
            else:
                return jsonify({'error': f"Error Code: {rescode}"}), rescode


    # 예외 처리들
    except urllib.error.HTTPError as http_err:
        error_message = http_err.read().decode('utf-8')
        print(f"HTTPError: {http_err.code} - {error_message}")
        return jsonify({'error': f"HTTPError: {http_err.code} - {error_message}"}), http_err.code
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)