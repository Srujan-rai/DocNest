import { initializeApp, cert, getApps } from 'firebase-admin/app';
import fs from 'fs';

export async function ensureFirebaseInitialized() {
  if (getApps().length === 0) {
    try {
      const raw = fs.readFileSync('./firebase-adminsdk.json', 'utf8');
      if (!raw) throw new Error("Empty Firebase JSON");
      const serviceAccount = JSON.parse(raw);
      initializeApp({ credential: cert(serviceAccount) });
    } catch (e) {
      console.warn("[Firebase Init Skipped]:", e.message);
      throw e;
    }
  }
}
