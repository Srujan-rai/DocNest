import { db } from "../../lib/db.js";
import { getUserFromToken } from "../../lib/auth.js";

export default async function handler(req, res) {
  const user = await getUserFromToken(req);
  if (!user) return res.status(401).json({ error: "Unauthorized" });

  if (req.method === "DELETE") {
    const id = parseInt(req.query.artifact_id);
    const artifact = await db.artifact.findUnique({ where: { id } });
    if (!artifact) return res.status(404).json({ error: "Not found" });

    const access = await db.access.findFirst({
      where: { userId: user.id, OR: [{ artifactId: id }, { nodeId: artifact.nodeId }], role: "ADMIN" }
    });
    if (!access) return res.status(403).json({ error: "Not allowed" });
    await db.artifact.delete({ where: { id } });
    return res.json({ message: `Deleted ${id}` });
  } else {
    res.status(405).end();
  }
}