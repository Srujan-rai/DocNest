import { db } from "../../lib/db.js";
import { getUserFromToken } from "../../lib/auth.js";

export default async function handler(req, res) {
  const user = await getUserFromToken(req);
  if (!user) return res.status(401).json({ error: "Unauthorized" });

  if (req.method === "GET") {
    const users = await db.user.findMany({
      include: { access: { include: { node: true } } },
    });
    return res.json(users.map(u => ({
      id: u.id,
      email: u.email,
      name: u.name,
      roles: u.access.map(a => ({ role: a.role, nodeId: a.nodeId, nodeName: a.node?.name }))
    })));
  } else if (req.method === "POST") {
    const { email, name } = req.body;
    const existing = await db.user.findUnique({ where: { email } });
    if (existing) return res.status(400).json({ error: "User already exists." });
    const created = await db.user.create({ data: { email, name } });
    return res.json(created);
  } else {
    res.status(405).end();
  }
}
