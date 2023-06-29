from unittest import mock

import pytest
import os
from backend.database import get_user


@pytest.fixture(autouse=True)
def mock_config_env_vars():
    with mock.patch.dict(os.environ, {"pocketbase_url": "http://example.com"}):
        yield


def test_get_user_returns_user_data():
    # Mocking the necessary dependencies
    mock_token = "mocked_token"
    mock_response = {
        "items": [{"id": 123, "name": "John Doe", "email": "johndoe@example.com"}]
    }

    with mock.patch("requests.get") as mock_get, mock.patch(
        "requests.Response"
    ) as mock_response_class:
        # Mock the response object
        mock_response_class.return_value.json.return_value = mock_response
        mock_response_class.return_value.raise_for_status.return_value = None

        # Mock the requests.get() function
        mock_get.return_value = mock_response_class

        # Call the function
        user = get_user(123)

        # Assertions
        assert user == {"id": 123, "name": "John Doe", "email": "johndoe@example.com"}
        mock_get.assert_called_once_with(
            f"{os.environ['pocketbase_url']}/api/collections/users/records?filter=(user_id='123')",
            params={"perPage": 1},
            headers={"Authorization": f"Bearer {mock_token}"},
        )
        mock_response_class.return_value.raise_for_status.assert_called_once()


def test_get_user_raises_exception_on_error():
    with mock.patch("requests.get") as mock_get, mock.patch(
        "requests.Response"
    ) as mock_response_class:
        # Mock the response object to simulate an error
        mock_response_class.return_value.raise_for_status.side_effect = Exception(
            "Error"
        )

        # Mock the requests.get() function
        mock_get.return_value = mock_response_class

        # Call the function and assert that it raises an exception
        with pytest.raises(Exception):
            get_user(123)

        mock_get.assert_called_once()
        mock_response_class.return_value.raise_for_status.assert_called_once()
