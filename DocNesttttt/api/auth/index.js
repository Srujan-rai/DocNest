import { db } from "../../lib/db.js";
import { getUserFromToken } from "../../lib/auth.js";

export default async function handler(req, res) {
  const user = await getUserFromToken(req, res);
  if (!user) return; // handled CORS or unauthorized

  if (req.method !== "POST") return res.status(405).end();

  const access_entries = await db.access.findMany({ where: { userId: user.id } });
  const roles = access_entries
    .filter(r => r.nodeId !== null)
    .map(r => ({ role: r.role, nodeId: r.nodeId }));

  const hasAdmin = roles.some(r => r.role === "ADMIN");
  const hasUser = roles.some(r => ["VIEWER", "EDITOR"].includes(r.role));

  return res.json({
    id: user.id,
    email: user.email,
    name: user.name,
    roles,
    isAdmin: hasAdmin,
    isUser: hasUser
  });
}
