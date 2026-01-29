def test_add_to_cart(client):
    """Test adding an item to the cart."""
    response = client.post('/api/cart', json={'sku': 'TEST-SHIRT-BLK-M', 'quantity': 1})
    assert response.status_code == 200
    data = response.get_json()
    assert len(data['items']) == 1
    assert data['items'][0]['sku'] == 'TEST-SHIRT-BLK-M'
    assert data['items'][0]['quantity'] == 1

def test_update_cart(client):
    """Test updating an item in the cart."""
    client.post('/api/cart', json={'sku': 'TEST-SHIRT-BLK-M', 'quantity': 1})
    response = client.post('/api/cart', json={'sku': 'TEST-SHIRT-BLK-M', 'quantity': 2})
    assert response.status_code == 200
    data = response.get_json()
    assert len(data['items']) == 1
    assert data['items'][0]['quantity'] == 2

def test_clear_cart(client):
    """Test clearing an item from the cart."""
    client.post('/api/cart', json={'sku': 'TEST-SHIRT-BLK-M', 'quantity': 1})
    response = client.post('/api/cart', json={'sku': 'TEST-SHIRT-BLK-M', 'quantity': 0})
    assert response.status_code == 200
    data = response.get_json()
    assert len(data['items']) == 0

def test_my_cart_page(authenticated_client):
    """Test that the my-cart page loads for an authenticated user."""
    response = authenticated_client.get('/my-cart', follow_redirects=True)
    assert response.status_code == 200
