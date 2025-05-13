# firebase.py
import firebase_admin
from firebase_admin import credentials,db

cred = credentials.Certificate("docnest-f85e2-firebase-adminsdk-fbsvc-4f30712b1b.json")
firebase_admin.initialize_app(cred,{
    "databaseURL":"https://docnest-f85e2-default-rtdb.asia-southeast1.firebasedatabase.app/"
})
