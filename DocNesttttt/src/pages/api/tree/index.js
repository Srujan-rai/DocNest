// src/pages/api/tree/index.js
import { db } from "../../../../lib/db.js"; // Adjust path if necessary
import { getUserFromToken, setCorsHeaders } from "../../../../lib/auth.js"; // Adjust path

function buildTree(flatNodes) {
  // Ensure nodes are plain objects if they are Prisma model instances
  const nodes = flatNodes.map(n => {
    const nodeData = { ...n }; // Shallow copy
    if (n.artifacts) {
      nodeData.artifacts = n.artifacts.map(a => ({ ...a })); // Shallow copy artifacts
    }
    if (n.children) { // If children are already populated in a specific way, ensure they are also plain
        // This buildTree expects children to be resolved from parentId, so this might be redundant
        // depending on how flatNodes are initially structured before passing here.
        // For now, we assume flatNodes are just nodes and artifacts are included.
    }
    return nodeData;
  });

  const nodeMap = {};
  nodes.forEach(n => nodeMap[n.id] = { ...n, children: [] }); // Initialize children array
  
  const tree = [];
  for (const nodeId in nodeMap) {
    const node = nodeMap[nodeId];
    if (node.parentId == null || !nodeMap[node.parentId]) { // Root node or orphan (treat as root)
      tree.push(node);
    } else {
      // Ensure parent's children array is initialized
      if (!nodeMap[node.parentId].children) {
        nodeMap[node.parentId].children = [];
      }
      nodeMap[node.parentId].children.push(node);
    }
  }
  return tree;
}

export default async function handler(req, res) {
  console.log(`[API /api/tree] TIMESTAMP: ${new Date().toISOString()} - Received request: ${req.method} ${req.url}`);
  
  if (setCorsHeaders(req, res)) { // Handle OPTIONS and set basic CORS headers
    console.log("[API /api/tree] OPTIONS preflight handled. Exiting.");
    return; 
  }
  console.log("[API /api/tree] Not an OPTIONS request, proceeding...");

  // This endpoint is critical for UI. Let's assume any authenticated user can fetch the tree.
  // If stricter permissions are needed (e.g., only users with some role), add checks here.
  const currentUser = await getUserFromToken(req);
  if (!currentUser) {
    console.log("[API /api/tree] Unauthorized access attempt. Sending 401.");
    return res.status(401).json({ error: "Unauthorized" });
  }
  console.log(`[API /api/tree] User ${currentUser.email} authenticated for ${req.method} request.`);

  if (req.method === "GET") {
    console.log("[API /api/tree] Processing GET request for full tree.");
    try {
      const flatNodesWithArtifacts = await db.node.findMany({ 
        include: { 
          artifacts: true // Include artifacts directly
        } 
      });
      
      // The buildTree function needs to correctly handle the included artifacts.
      // The current buildTree might need adjustment if artifacts aren't nested correctly by it.
      // For simplicity, let's assume buildTree can handle nodes that already have an 'artifacts' array.
      // Or, you might fetch artifacts separately and merge them.
      // The provided buildTree primarily focuses on parent-child node relationships.

      // Let's refine how artifacts are associated if buildTree doesn't do it.
      const nodes = await db.node.findMany({});
      const artifacts = await db.artifact.findMany({});
      
      const nodeMapWithArtifacts = {};
      nodes.forEach(n => {
        nodeMapWithArtifacts[n.id] = { ...n, children: [], artifacts: [] };
      });
      artifacts.forEach(a => {
        if (nodeMapWithArtifacts[a.nodeId]) {
          nodeMapWithArtifacts[a.nodeId].artifacts.push(a);
        }
      });

      const tree = [];
      for (const nodeId in nodeMapWithArtifacts) {
        const node = nodeMapWithArtifacts[nodeId];
        if (node.parentId == null || !nodeMapWithArtifacts[node.parentId]) {
          tree.push(node);
        } else {
          if (!nodeMapWithArtifacts[node.parentId].children) { // Should be initialized
            nodeMapWithArtifacts[node.parentId].children = [];
          }
          nodeMapWithArtifacts[node.parentId].children.push(node);
        }
      }
      
      console.log("[API /api/tree] Successfully fetched and built tree. Sending 200 OK.");
      return res.status(200).json(tree); // Send the processed tree

    } catch (e) {
      console.error("[API /api/tree] Error fetching or building tree:", e);
      return res.status(500).json({ error: "Failed to fetch tree structure.", details: e.message });
    }
  } else {
    console.log(`[API /api/tree] Method ${req.method} not allowed. Sending 405.`);
    res.setHeader('Allow', ['GET', 'OPTIONS']);
    return res.status(405).json({ error: `Method ${req.method} Not Allowed on /api/tree` });
  }
}
