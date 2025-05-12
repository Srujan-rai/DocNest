import { db } from "../../../../lib/db.js";
import { getUserFromToken } from "../../../../lib/auth.js";

function buildTree(flatNodes) {
  const nodeMap = {};
  flatNodes.forEach(n => nodeMap[n.id] = { ...n, children: [] });
  const tree = [];
  for (const node of Object.values(nodeMap)) {
    if (node.parentId == null) {
      tree.push(node);
    } else if (nodeMap[node.parentId]) {
      nodeMap[node.parentId].children.push(node);
    }
  }
  return tree;
}

function findSubtree(tree, targetId) {
  for (const node of tree) {
    if (node.id === targetId) return node;
    if (node.children?.length) {
      const sub = findSubtree(node.children, targetId);
      if (sub) return sub;
    }
  }
  return null;
}

export default async function handler(req, res) {
  const user = await getUserFromToken(req);
  if (!user) return res.status(401).json({ error: "Unauthorized" });

  if (req.method !== "GET") return res.status(405).end();
  const nodeId = parseInt(req.query.node_id);
  const root = await db.node.findUnique({ where: { id: nodeId } });
  if (!root) return res.status(404).json({ error: "Node not found" });
  const flat = await db.node.findMany({ include: { artifacts: true } });
  const tree = buildTree(flat);
  const subtree = findSubtree(tree, nodeId);
  return res.json(subtree || { message: "Subtree not found" });
}
