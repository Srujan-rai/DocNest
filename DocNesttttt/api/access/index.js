import { db } from "../../lib/db.js";
import { getUserFromToken } from "../../lib/auth.js";

export default async function handler(req, res) {
  const currentUser = await getUserFromToken(req);
  if (!currentUser) return res.status(401).json({ error: "Unauthorized" });

  const assertAdminAccess = async (nodeId) => {
    const access = await db.access.findFirst({ where: { userId: currentUser.id, nodeId, role: "ADMIN" } });
    if (!access) throw new Error("Only ADMINs can modify access.");
  };

  const getAllChildNodes = async (parentId) => {
    const result = [];
    const recurse = async (currentId) => {
      const children = await db.node.findMany({ where: { parentId: currentId } });
      for (const child of children) {
        result.push(child.id);
        await recurse(child.id);
      }
    };
    await recurse(parentId);
    return result;
  };

  if (req.method === "POST") {
    const { email, nodeId, role } = req.body;
    try {
      await assertAdminAccess(nodeId);
      let user = await db.user.findUnique({ where: { email } });
      if (!user) user = await db.user.create({ data: { email } });
      const existing = await db.access.findFirst({ where: { userId: user.id, nodeId } });
      if (existing) return res.status(400).json({ error: `User already has ${existing.role} access.` });
      const access = await db.access.create({ data: { userId: user.id, nodeId, role } });
      return res.json({ message: "Access granted", accessId: access.id });
    } catch (e) {
      return res.status(403).json({ error: e.message });
    }
  } else if (req.method === "PUT") {
    const { email, nodeId, role } = req.body;
    try {
      await assertAdminAccess(nodeId);
      const user = await db.user.findUnique({ where: { email } });
      if (!user) return res.status(404).json({ error: "User not found" });
      const allNodeIds = [nodeId].concat(await getAllChildNodes(nodeId));
      for (const nid of allNodeIds) {
        const existing = await db.access.findFirst({ where: { userId: user.id, nodeId: nid } });
        if (existing) {
          await db.access.update({ where: { id: existing.id }, data: { role } });
        } else {
          await db.access.create({ data: { userId: user.id, nodeId: nid, role } });
        }
      }
      return res.json({ message: "Role updated recursively", updatedNodes: allNodeIds });
    } catch (e) {
      return res.status(403).json({ error: e.message });
    }
  } else if (req.method === "DELETE") {
    const { email, nodeId } = req.body;
    try {
      await assertAdminAccess(nodeId);
      const user = await db.user.findUnique({ where: { email } });
      if (!user) return res.status(404).json({ error: "User not found" });
      const allNodeIds = [nodeId].concat(await getAllChildNodes(nodeId));
      for (const nid of allNodeIds) {
        const access = await db.access.findFirst({ where: { userId: user.id, nodeId: nid } });
        if (access) await db.access.delete({ where: { id: access.id } });
      }
      return res.json({ message: "Access revoked recursively", revokedNodes: allNodeIds });
    } catch (e) {
      return res.status(403).json({ error: e.message });
    }
  } else {
    res.status(405).end();
  }
}
