from functions import *
from main import app
from limiter import RateLimiter

redis_host = 'localhost'
redis_port = 6379
time_window = 60  # 60 seconds

limiter = RateLimiter(redis_host, redis_port, time_window)

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_code_rate_limit(client):
    endpoint = "http://127.0.0.1:5000/download/test.py"
    
    # Send requests exceeding the rate limit
    for _ in range(21): 
        response = requests.get(endpoint)
    assert response.status_code == 429  # 429 Too Many Requests

def test_document_rate_limit(client):
    endpoint = "http://127.0.0.1:5000/download/winning_metrics.pdf"
    
    # Send requests exceeding the rate limit
    for _ in range(11):  
        response = requests.get(endpoint)
    assert response.status_code == 429  # 429 Too Many Requests

def test_image_rate_limit(client):
    endpoint = "http://127.0.0.1:5000/download/Profile.jpg"
    
    # Send requests exceeding the rate limit
    for _ in range(6):  
        response = requests.get(endpoint)
    assert response.status_code == 429  # 429 Too Many Requests

def test_sheet_rate_limit(client):
    endpoint = "http://127.0.0.1:5000/download/investments_VC.csv"
    
    # Send requests exceeding the rate limit
    for _ in range(6):  
        response = requests.get(endpoint)
    assert response.status_code == 429  # 429 Too Many Requests