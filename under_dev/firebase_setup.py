# firebase.py
import firebase_admin
from firebase_admin import credentials

cred = credentials.Certificate("docnest-f85e2-firebase-adminsdk-fbsvc-4f30712b1b.json")
firebase_admin.initialize_app(cred)
