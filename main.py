from flask import Flask, request, jsonify
import requests
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad
from google.protobuf.descriptor_pb2 import DescriptorProto, FieldDescriptorProto
from google.protobuf.descriptor import MakeDescriptor
from google.protobuf.message_factory import GetMessageClass
import urllib3
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# Configuration
DEFAULT_TOKEN = os.getenv('DEFAULT_TOKEN', '')

def encrypt_api(plain_text):
    plain_text = bytes.fromhex(plain_text)
    key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
    iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return cipher.encrypt(pad(plain_text, AES.block_size)).hex()

def create_dynamic_protobuf():
    descriptor = DescriptorProto()
    descriptor.name = "DynamicMessage"
    
    field = descriptor.field.add()
    field.name = "field_8"
    field.number = 8
    field.label = FieldDescriptorProto.LABEL_OPTIONAL
    field.type = FieldDescriptorProto.TYPE_STRING
    
    message_descriptor = MakeDescriptor(descriptor)
    return GetMessageClass(message_descriptor)

def encode_protobuf(field_8_value):
    message_class = create_dynamic_protobuf()
    message = message_class()
    message.field_8 = field_8_value
    return message.SerializeToString().hex()

@app.route('/')
def home():
    return jsonify({
        "status": "running",
        "endpoints": {
            "GET /": "API info",
            "POST /update_bio": "Update Free Fire bio",
            "POST /update_bio_with_token": "Update bio with custom token"
        },
        "usage": {
            "update_bio": {
                "method": "POST",
                "url": "/update_bio",
                "body": {"bio": "your new bio"}
            },
            "update_bio_with_token": {
                "method": "POST",
                "url": "/update_bio_with_token",
                "body": {"token": "your_jwt_token", "bio": "your new bio"}
            }
        }
    })

@app.route('/update_bio', methods=['POST'])
def update_bio_default():
    if not DEFAULT_TOKEN:
        return jsonify({"error": "Default token not configured"}), 500
    
    data = request.json
    user_bio = data.get('bio')
    
    if not user_bio:
        return jsonify({"error": "Bio is required"}), 400

    return perform_bio_update(DEFAULT_TOKEN, user_bio)

@app.route('/update_bio_with_token', methods=['POST'])
def update_bio_custom():
    data = request.json
    token = data.get('token')
    user_bio = data.get('bio')
    
    if not token or not user_bio:
        return jsonify({"error": "Both token and bio are required"}), 400

    return perform_bio_update(token, user_bio)

def perform_bio_update(token, bio):
    try:
        encoded_bio = encode_protobuf(bio)
        encrypted_data = encrypt_api(f'1011{encoded_bio}5a006200')

        url = 'https://client.ind.freefiremobile.com/UpdateSocialBasicInfo'
        headers = {
            'Expect': '100-continue',
            'Authorization': f'Bearer {token}',
            'X-Unity-Version': '2018.4.11f1',
            'X-GA': 'v1 1',
            'ReleaseVersion': 'OB49',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 9; Redmi Note 5 MIUI/V11.0.3.0.PEIMIXM)',
            'Host': 'clientbp.ggblueshark.com',
            'Connection': 'Keep-Alive',
            'Accept-Encoding': 'gzip'
        }

        response = requests.post(url, data=bytes.fromhex(encrypted_data), headers=headers, verify=False)
        
        if response.status_code == 200:
            return jsonify({
                "status": "success",
                "message": "Bio updated successfully",
                "bio": bio
            })
        else:
            return jsonify({
                "status": "error",
                "message": f"Free Fire API request failed with status {response.status_code}",
                "response": response.text
            }), 400
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": "An error occurred while processing your request",
            "error": str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))