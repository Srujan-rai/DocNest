// src/pages/api/auth/index.js
import { db } from "../../../../lib/db.js";
import { getUserFromToken, setCorsHeaders } from "../../../../lib/auth.js";

export default async function handler(req, res) {
  console.log(`[API /api/auth] TIMESTAMP: ${new Date().toISOString()} - Received request: ${req.method} ${req.url}`);
  console.log("[API /api/auth] typeof setCorsHeaders:", typeof setCorsHeaders);
  console.log("[API /api/auth] typeof getUserFromToken:", typeof getUserFromToken);

  if (typeof setCorsHeaders !== 'function') {
    console.error("[API /api/auth] CRITICAL: setCorsHeaders is NOT a function after import. Check lib/auth.js export.");
    res.setHeader('Access-Control-Allow-Origin', 'http://127.0.0.1:5500');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With');
    if (req.method === 'OPTIONS') return res.status(204).end();
    return res.status(500).json({ error: "Server configuration error (CORS handler missing)." });
  }

  if (setCorsHeaders(req, res)) {
    console.log("[API /api/auth] OPTIONS preflight handled by setCorsHeaders. Exiting.");
    return; 
  }

  console.log("[API /api/auth] Not an OPTIONS request, or OPTIONS already handled, proceeding...");

  if (req.method !== "POST") {
    console.log(`[API /api/auth] Method ${req.method} not allowed. Sending 405.`);
    res.setHeader('Allow', ['POST', 'OPTIONS']);
    return res.status(405).json({ error: `Method ${req.method} Not Allowed` });
  }

  console.log("[API /api/auth] Processing POST request...");

  try {
    if (typeof getUserFromToken !== 'function') {
        console.error("[API /api/auth] CRITICAL: getUserFromToken is NOT a function after import. Check lib/auth.js export.");
        return res.status(500).json({ error: "Server configuration error (Auth handler missing)." });
    }
    const user = await getUserFromToken(req); 

    if (!user) {
      console.log("[API /api/auth] getUserFromToken returned null or false. Sending 401.");
      return res.status(401).json({ error: "Unauthorized: Invalid token, user not found in DB, or Firebase initialization issue." });
    }

    console.log(`[API /api/auth] User ${user.email} (ID: ${user.id}, Firebase UID: ${user.firebaseUid}) authenticated. Fetching access entries.`);
    
    const access_entries = await db.access.findMany({
      where: { userId: user.id }
    });
    console.log(`[API /api/auth] Found ${access_entries.length} access entries for user ${user.id}.`);

    const nodeRoles = access_entries
      .filter(r => r.nodeId !== null)
      .map(r => ({ role: r.role, nodeId: r.nodeId }));

    // --- THIS IS THE CORRECTED LINE ---
    const isAdmin = nodeRoles.some(r => r.role === "ADMIN"); 
    // This checks if the user has an "ADMIN" role on ANY node.
    // Alternatively, if you still want to check a global user.role AND node-specific roles:
    // const hasGlobalAdminRole = user.role === "ADMIN";
    // const hasNodeAdminRole = nodeRoles.some(r => r.role === "ADMIN");
    // const isAdmin = hasGlobalAdminRole || hasNodeAdminRole;
    // --- END CORRECTION ---

    console.log(`[API /api/auth] User ${user.email}, isAdmin determined as: ${isAdmin}. Sending 200 OK response.`);
    
    return res.status(200).json({
      id: user.id,
      email: user.email,
      name: user.name,
      roles: nodeRoles,
      isAdmin: isAdmin,
      isUser: !isAdmin && (nodeRoles.length > 0 || (user.role && ["VIEWER", "EDITOR"].includes(user.role))) // Adjusted isUser logic
    });

  } catch (error) {
    console.error("[API /api/auth] CRITICAL ERROR in POST handler:", error);
    if (!res.headersSent) {
      console.log("[API /api/auth] Sending 500 Internal Server Error due to caught exception.");
      return res.status(500).json({ error: "Internal Server Error. Please check server logs.", details: error.message });
    } else {
      console.log("[API /api/auth] Headers already sent, cannot send 500 error for caught exception.");
    }
  }
}