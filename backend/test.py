# test_upload.py

from supabase import create_client
import os
from dotenv import load_dotenv
load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')  # Replace with actual Supabase URL
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_KEY')  # Replace with actual service_role key
SUPABASE_BUCKET = "docnest-uploads"
print("URL:", SUPABASE_URL)
print("KEY:", SUPABASE_SERVICE_ROLE_KEY, "...")


supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Path to local file you want to upload
file_path = "under_dev/db.py"
file_name = os.path.basename(file_path)

# Read the file content
with open(file_path, "rb") as f:
    file_content = f.read()

# Upload to Supabase Storage
try:
    result = supabase.storage.from_(SUPABASE_BUCKET).upload(
        path=file_name,
        file=file_content,
        file_options={"content-type": "application/octet-stream"}  # Or use "text/plain", "application/pdf", etc.
    )
    print("✅ Upload successful!")
    print(result)

except Exception as e:
    print("❌ Upload failed!")
    print("Error:", e)
