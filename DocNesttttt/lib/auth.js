// lib/auth.js
import { getAuth } from 'firebase-admin/auth';
import { db } from './db.js';
import { ensureFirebaseInitialized } from './firebase-init.js';

export async function getUserFromToken(req, res) {
  // Apply CORS headers
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization");

  if (req.method === "OPTIONS") {
    res.status(200).end();
    return;
  }

  try {
    await ensureFirebaseInitialized();
  } catch (e) {
    console.warn("[Firebase Init Error]:", e.message);
    return null;
  }

  const authHeader = req.headers.authorization;
  if (!authHeader?.startsWith("Bearer ")) return null;
  const idToken = authHeader.split("Bearer ")[1];
  try {
    const decoded = await getAuth().verifyIdToken(idToken);
    const email = decoded.email;
    return await db.user.findUnique({ where: { email } });
  } catch {
    return null;
  }
}
