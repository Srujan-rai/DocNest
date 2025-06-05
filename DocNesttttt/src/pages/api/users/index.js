// src/pages/api/users/index.js
import { db } from "../../../../lib/db.js"; // Ensure this path is correct
import { getUserFromToken, setCorsHeaders } from "../../../../lib/auth.js"; // Ensure this path is correct

export default async function handler(req, res) {
  console.log(`[API /api/users] TIMESTAMP: ${new Date().toISOString()} - Received request: ${req.method} ${req.url}`);

  if (setCorsHeaders(req, res)) {
    console.log("[API /api/users] OPTIONS preflight handled. Exiting.");
    return; 
  }
  console.log("[API /api/users] Not an OPTIONS request, proceeding...");

  const currentUser = await getUserFromToken(req);
  if (!currentUser) {
    console.log("[API /api/users] Unauthorized access attempt. Sending 401.");
    return res.status(401).json({ error: "Unauthorized" });
  }
  console.log(`[API /api/users] User ${currentUser.email} (ID: ${currentUser.id}) authenticated for ${req.method} request.`);

  if (req.method === "GET") {
    console.log("[API /api/users] Processing GET request to list users.");
    try {
      // Authorization: Check if the current user has an ADMIN role on any node
      const userAccessEntriesForAuth = await db.access.findMany({
        where: { userId: currentUser.id, role: "ADMIN" }
      });
      const isNodeAdminForListing = userAccessEntriesForAuth.length > 0;

      if (!isNodeAdminForListing) { 
        console.log(`[API /api/users] User ${currentUser.email} is not authorized to list all users (Node Admin: ${isNodeAdminForListing}). Sending 403.`);
        return res.status(403).json({ error: "You do not have permission to view all users." });
      }
      console.log(`[API /api/users] User ${currentUser.email} is authorized (Node Admin: ${isNodeAdminForListing}). Fetching users.`);

      const users = await db.user.findMany({
        include: { 
          access: { 
            include: { 
              node: { select: { name: true, id: true } }, 
              artifact: { select: { title: true, id: true } } 
            } 
          } 
        },
      });

      const formattedUsers = users.map(u => ({
        id: u.id,
        email: u.email,
        name: u.name,
        // 'role': u.role, // This would be undefined if 'role' is not on User model
        accessRoles: u.access.map(a => ({ 
          role: a.role, 
          nodeId: a.nodeId, 
          nodeName: a.node?.name,
          artifactId: a.artifactId,
          artifactTitle: a.artifact?.title
        }))
      }));
      console.log(`[API /api/users] Successfully fetched ${formattedUsers.length} users. Sending 200 OK.`);
      return res.status(200).json(formattedUsers);

    } catch (e) {
      console.error("[API /api/users] Error fetching users:", e);
      return res.status(500).json({ error: "Failed to fetch users.", details: e.message });
    }
  } else if (req.method === "POST") {
    console.log("[API /api/users] Processing POST request to create user with body:", req.body);
    
    // Authorization for creating users: Check if current user is an ADMIN on any node
    const userAccessEntriesForAuth = await db.access.findMany({
        where: { userId: currentUser.id, role: "ADMIN" }
    });
    const canCreateUsers = userAccessEntriesForAuth.length > 0;

    if (!canCreateUsers) { 
        console.log(`[API /api/users] User ${currentUser.email} is not authorized to create users (Node Admin: ${canCreateUsers}). Sending 403.`);
        return res.status(403).json({ error: "You do not have permission to create users." });
    }
    console.log(`[API /api/users] User ${currentUser.email} is authorized (Node Admin: ${canCreateUsers}) to create users.`);


    const { email, name, role } = req.body; // 'role' here would be for the NEW user's global role if you implement it

    if (!email) {
        console.log("[API /api/users] Email is required to create a user. Sending 400.");
        return res.status(400).json({ error: "Email is required." });
    }

    try {
        const existing = await db.user.findUnique({ where: { email } });
        if (existing) {
            console.log(`[API /api/users] User with email ${email} already exists. Sending 400.`);
            return res.status(400).json({ error: "User already exists." });
        }
        
        const dataToCreate = { email, name: name || null };
        // If you add a global 'role' to your User model in Prisma and want to set it on creation:
        // if (role) { 
        //     dataToCreate.role = role;
        // }

        const createdUser = await db.user.create({ data: dataToCreate });
        console.log("[API /api/users] User created successfully:", createdUser);
        // Note: You might want to grant the new user some default access or a default global role here.
        return res.status(201).json(createdUser);
    } catch (e) {
        console.error("[API /api/users] Error creating user:", e);
        return res.status(500).json({ error: "Failed to create user.", details: e.message });
    }
  } else {
    console.log(`[API /api/users] Method ${req.method} not allowed. Sending 405.`);
    res.setHeader('Allow', ['GET', 'POST', 'OPTIONS']);
    return res.status(405).json({ error: `Method ${req.method} Not Allowed on /api/users` });
  }
}
