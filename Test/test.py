from functions import *
from main import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_image_rate_limit(client):
    file_name = 'image.jpg'
    response = client.get(f'/download/{file_name}')
    assert response.status_code == 200
    assert response.data.decode('utf-8') == f'Downloading file: {file_name}'

def test_rate_limit_exceeded():
    endpoint = "http://127.0.0.1:5000/"
    
    # Send requests exceeding the rate limit
    for _ in range(15):  # Assuming the rate limit is set to 10 requests per minute
        response = requests.get(endpoint)
        assert response.status_code == 429  # 429 Too Many Requests

def test_document_rate_limit(client):
    file_name = 'document.docx'
    response = client.get(f'/download/{file_name}')
    assert response.status_code == 200
    assert response.data.decode('utf-8') == f'Downloading file: {file_name}'

def test_code_rate_limit(client):
    file_name = 'code.py'
    response = client.get(f'/download/{file_name}')
    assert response.status_code == 200
    assert response.data.decode('utf-8') == f'Downloading file: {file_name}'

def test_unknown_file_type_rate_limit(client):
    file_name = 'unknown.xyz'
    response = client.get(f'/download/{file_name}')
    assert response.status_code == 429  # 429 indicates Too Many Requests

def test_nonexistent_file_type_rate_limit(client):
    file_name = 'nonexistent.xyz'
    response = client.get(f'/download/{file_name}')
    assert response.status_code == 429

def test_default_rate_limit(client):
    file_name = 'default.xyz'
    response = client.get(f'/download/{file_name}')
    assert response.status_code == 429