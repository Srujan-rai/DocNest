// lib/auth.js
import { getAuth } from 'firebase-admin/auth';
import { db } from './db.js'; // Ensure this path is correct from the root of your Next.js project
import { ensureFirebaseInitialized } from './firebase-init.js'; // Ensure this path is correct

const ALLOWED_ORIGIN = 'http://127.0.0.1:5500'; // Your frontend origin for development

// Export this function for setting CORS headers and handling OPTIONS
export function setCorsHeaders(req, res) {
  res.setHeader('Access-Control-Allow-Origin', ALLOWED_ORIGIN);
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With');
  res.setHeader('Access-Control-Allow-Credentials', 'true');

  if (req.method === 'OPTIONS') {
    console.log(`CORS: Responding to OPTIONS preflight for ${req.url} from origin ${req.headers.origin}`);
    res.status(204).end(); // 204 No Content is standard for preflight
    return true; // Indicates preflight was handled
  }
  return false; // Not a preflight, continue processing
}

// Export this function for getting user from token
export async function getUserFromToken(req) { // 'res' parameter removed
  try {
    await ensureFirebaseInitialized();
  } catch (e) {
    console.error("[Firebase Init Error in getUserFromToken]:", e.message);
    return null;
  }

  const authHeader = req.headers.authorization;
  if (!authHeader?.startsWith("Bearer ")) {
    console.log("getUserFromToken: No Bearer token found in Authorization header.");
    return null;
  }
  const idToken = authHeader.split("Bearer ")[1];

  try {
    const decodedToken = await getAuth().verifyIdToken(idToken);
    console.log(`getUserFromToken: Token for ${decodedToken.email} verified by Firebase.`);

    const userFromDb = await db.user.findUnique({
      where: { email: decodedToken.email },
      // include: { yourUserRoleRelation: true } // If you have roles linked to user model
    });

    if (!userFromDb) {
      console.warn(`getUserFromToken: User ${decodedToken.email} (UID: ${decodedToken.uid}) verified by Firebase but not found in local DB.`);
      // For an admin system, typically the user should already exist in your DB.
      return null; 
    }
    
    // Return relevant user details from your database
    return { 
        id: userFromDb.id,
        email: userFromDb.email,
        name: userFromDb.name || decodedToken.name, 
        role: userFromDb.role, // Assuming your Prisma User model has a 'role' field
        firebaseUid: decodedToken.uid
        // ... any other fields from your User model
    };

  } catch (error) {
    console.error("getUserFromToken: Error verifying ID token or fetching user:", error.message);
    return null;
  }
}
