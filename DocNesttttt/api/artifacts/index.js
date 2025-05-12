import { db } from "../../lib/db.js";
import { getUserFromToken } from "../../lib/auth.js";

export default async function handler(req, res) {
  const user = await getUserFromToken(req);
  if (!user) return res.status(401).json({ error: "Unauthorized" });

  if (req.method === "POST") {
    const { title, description, link, nodeId } = req.body;
    const access = await db.access.findFirst({
      where: { userId: user.id, nodeId, role: { in: ["ADMIN", "EDITOR"] } }
    });
    if (!access) return res.status(403).json({ error: "No permission." });

    const artifact = await db.artifact.create({
      data: { title, description, link, nodeId, createdBy: user.id }
    });
    await db.access.create({ data: { userId: user.id, artifactId: artifact.id, role: "ADMIN" } });
    return res.json(artifact);
  } else {
    res.status(405).end();
  }
}
