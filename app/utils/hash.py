import hashlib
import uuid
import secrets
import string


def generate_random_string(length: int = 32) -> str:
    """
    Generate a random string of specified length

    Parameters:
    - length: Length of the string to generate

    Returns:
    - Random string
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_transaction_hash() -> str:
    """
    Generate a unique transaction hash

    Returns:
    - Transaction hash
    """
    # Generate a UUID and hash it
    random_id = str(uuid.uuid4())
    hash_obj = hashlib.sha256(random_id.encode())

    # Return the first 24 characters of the hash
    return hash_obj.hexdigest()[:24]


def hash_data(data: str) -> str:
    """
    Hash data using SHA-256

    Parameters:
    - data: Data to hash

    Returns:
    - Hashed data
    """
    hash_obj = hashlib.sha256(data.encode())
    return hash_obj.hexdigest()


def generate_api_key() -> str:
    """
    Generate an API key

    Returns:
    - API key
    """
    return generate_random_string(32)


def generate_webhook_secret() -> str:
    """
    Generate a webhook secret

    Returns:
    - Webhook secret
    """
    return generate_random_string(64)