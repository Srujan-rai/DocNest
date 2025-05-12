import { db } from "../../lib/db.js";

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

export default async function handler(req, res) {
  if (req.method !== "GET") return res.status(405).end();
  const flat = await db.node.findMany({ include: { artifacts: true } });
  return res.json(buildTree(flat));
}