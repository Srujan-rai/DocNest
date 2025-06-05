import { db } from "../../../../lib/db.js";
import { getUserFromToken } from "../../../../lib/auth.js";

export default async function handler(req, res) {
  const user = await getUserFromToken(req);
  if (!user) return res.status(401).json({ error: "Unauthorized" });

  const nodeId = parseInt(req.query.node_id);
  if (req.method === "GET") {
    const access = await db.access.findFirst({ where: { userId: user.id, nodeId, role: { in: ["ADMIN", "EDITOR", "VIEWER"] } } });
    if (!access) return res.status(403).json({ error: "No access" });
    const node = await db.node.findUnique({ where: { id: nodeId } });
    if (!node) return res.status(404).json({ error: "Not found" });
    return res.json(node);
  } else {
    res.status(405).end();
  }
}
