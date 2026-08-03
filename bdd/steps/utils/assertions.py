def assert_response_ok(response, action, expected_status=200):
    assert response.status_code == expected_status, \
        f"\n{action} failed: expected HTTP {expected_status}, got {response.status_code} - {response.content}\n"
