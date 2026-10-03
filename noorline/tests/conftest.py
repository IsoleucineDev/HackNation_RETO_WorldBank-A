import os
from cryptography.fernet import Fernet
os.environ["NOORLINE_KEY"] = Fernet.generate_key().decode()
os.environ.pop("NOORLINE_API_KEY", None)
