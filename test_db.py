from dotenv import load_dotenv
import pathlib, os
load_dotenv(pathlib.Path(__file__).parent / ".env")
from sqlalchemy import create_engine, text
url = f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
print("URL:", url)
e = create_engine(url, pool_pre_ping=True)
with e.connect() as c:
    print("OK :", c.execute(text("SELECT COUNT(*) FROM clients")).fetchone())
