from flask import Flask, jsonify, request
import os
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient, __version__
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from msrest.authentication import CognitiveServicesCredentials
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
from flask_cors import CORS
from werkzeug.utils import secure_filename
import time

load_dotenv()
key = os.getenv("AZURE_KEY")
endpoint = os.getenv("AZURE_ENDPOINT")
connect_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
debug = os.getenv('DEBUG')

os.environ['TZ'] = 'Asia/Taipei'

# Set credentials
credentials = CognitiveServicesCredentials(key)
# Create client
client = ComputerVisionClient(endpoint, credentials)


class OCRService:
    @staticmethod
    def azureOCR(filePath):
        # file = open(filePath, 'rb')
        # Async SDK call that "reads" the image
        response = client.read(filePath, raw=True)

        # Get ID from returned headers
        operation_location = response.headers["Operation-Location"]
        operation_id = operation_location.split("/")[-1]

        # SDK call that gets what is read
        while True:
            result = client.get_read_result(operation_id)
            if result.status.lower() not in ['notstarted', 'running']:
                break
            print('Waiting for result...')
            time.sleep(1)
        return result

    @staticmethod
    def getText(filePath):
        text = ''
        result = OCRService.azureOCR(filePath)
        if result.status == OperationStatusCodes.succeeded:
            for readResult in result.analyze_result.read_results:
                for line in readResult.lines:
                    print(line.text)
                    text += line.text
                print()
        return text

class StorageService:
    @staticmethod
    def upload(file, filename):
        try:
            blob_service_client = BlobServiceClient.from_connection_string(
                connect_str)
            blob_client = blob_service_client.get_blob_client(
                container='test-storage', blob=filename)
            blob_client.upload_blob(file)
            content = OCRService.getText(blob_client.url)
            # document = DatabaseService.addNewDocument(filename, blob_client.url, content)
            # print(document)
            return (blob_client.url, content)
        except Exception as e:
            return e


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})


ALLOWED_EXTENSIONS = set(['pdf', 'png', 'jpg', 'jpeg'])
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app.route('/ocr', methods=['POST'])
def ocr():
    files = request.files.getlist('document[]')
    print(files);
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            url, content = StorageService.upload(file, filename)
    return jsonify({'success': True, 'url': url, 'content': content})

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=debug)
