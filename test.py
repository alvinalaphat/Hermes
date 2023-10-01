from functions import *
from main import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_image_rate_limit(client):
    endpoint = "http://127.0.0.1:5000/download/Profile2.jpg"
    
    # Send requests exceeding the rate limit
    for _ in range(11):  # Assuming the rate limit is set to 10 requests per minute
        response = requests.get(endpoint)
        assert response.status_code == 429  # 429 Too Many Requests

def test_document_rate_limit(client):
    endpoint = "http://127.0.0.1:5000/download/Payslip.pdf"
    
    # Send requests exceeding the rate limit
    for _ in range(21):  # Assuming the rate limit is set to 10 requests per minute
        response = requests.get(endpoint)
        assert response.status_code == 429  # 429 Too Many Requests