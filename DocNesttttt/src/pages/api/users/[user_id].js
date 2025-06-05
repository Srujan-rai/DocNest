import { db } from "../../../../lib/db.js";
import { getUserFromToken } from "../../../../lib/auth.js";

export default async function handler(req, res) {
  const user = await getUserFromToken(req);
  if (!user) return res.status(401).json({ error: "Unauthorized" });

  const id = parseInt(req.query.user_id);
  if (req.method === "PUT") {
    const { email, name } = req.body;
    const existing = await db.user.findUnique({ where: { id } });
    if (!existing) return res.status(404).json({ error: "User not found." });
    const updated = await db.user.update({ where: { id }, data: { email, name } });
    return res.json(updated);
  } else if (req.method === "DELETE") {
    const existing = await db.user.findUnique({ where: { id } });
    if (!existing) return res.status(404).json({ error: "User not found." });
    const deleted = await db.user.delete({ where: { id } });
    return res.json(deleted);
  } else {
    res.status(405).end();
  }
}
