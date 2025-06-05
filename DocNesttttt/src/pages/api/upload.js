// src/pages/api/upload.js
import formidable from "formidable"; // For formidable v3+
import { createClient } from "@supabase/supabase-js";
import { db } from "../../../lib/db.js"; // CORRECTED PATH
import { getUserFromToken, setCorsHeaders } from "../../../lib/auth.js"; // CORRECTED PATH
import { v4 as uuidv4 } from "uuid";
import fs from 'fs'; // Node.js File System module

// Disable Next.js body parsing for this route to allow formidable to handle multipart/form-data
export const config = {
  api: {
    bodyParser: false,
  },
};

// Initialize Supabase client - ensure these ENV vars are set in your .env file
const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_KEY; // This should be the service_role key for backend operations
let supabase;
if (supabaseUrl && supabaseKey) {
  supabase = createClient(supabaseUrl, supabaseKey);
} else {
  console.error("Supabase URL or Key is not defined in environment variables. File uploads will fail.");
}

export default async function handler(req, res) {
  console.log(`[API /api/upload] TIMESTAMP: ${new Date().toISOString()} - Received request: ${req.method} ${req.url}`);
  // Logging imported functions to ensure they are not undefined
  console.log("[API /api/upload] typeof setCorsHeaders:", typeof setCorsHeaders);
  console.log("[API /api/upload] typeof getUserFromToken:", typeof getUserFromToken);

  if (typeof setCorsHeaders !== 'function') {
    console.error("[API /api/upload] CRITICAL: setCorsHeaders is NOT a function after import. Check lib/auth.js export.");
    res.setHeader('Access-Control-Allow-Origin', 'http://127.0.0.1:5500'); 
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With');
    if (req.method === 'OPTIONS') return res.status(204).end();
    return res.status(500).json({ error: "Server configuration error (CORS handler missing)." });
  }

  if (setCorsHeaders(req, res)) {
    console.log("[API /api/upload] OPTIONS preflight handled by setCorsHeaders. Exiting.");
    return;
  }
  console.log("[API /api/upload] Not an OPTIONS request, or OPTIONS already handled, proceeding...");

  const currentUser = await getUserFromToken(req);
  if (!currentUser) {
    console.log("[API /api/upload] Unauthorized (no valid token/user). Sending 401.");
    return res.status(401).json({ error: "Unauthorized" });
  }
  console.log(`[API /api/upload] User ${currentUser.email} authenticated for ${req.method} request.`);

  if (req.method !== "POST") {
    console.log(`[API /api/upload] Method ${req.method} not allowed. Sending 405.`);
    res.setHeader('Allow', ['POST', 'OPTIONS']);
    return res.status(405).json({ error: `Method ${req.method} Not Allowed` });
  }

  if (!supabase) {
    console.error("[API /api/upload] Supabase client not initialized. Cannot process upload.");
    return res.status(500).json({ error: "File upload service is not configured." });
  }

  console.log("[API /api/upload] Processing POST request for file upload...");

  const form = formidable({ multiples: false }); 

  form.parse(req, async (err, fields, files) => {
    if (err) {
      console.error("[API /api/upload] Error parsing form data:", err);
      return res.status(500).json({ error: "Error parsing form data.", details: err.message });
    }

    console.log("[API /api/upload] Form parsed. Fields:", fields, "Files:", files);

    const title = Array.isArray(fields.title) ? fields.title[0] : fields.title;
    const description = Array.isArray(fields.description) ? fields.description[0] : fields.description;
    const nodeIdString = Array.isArray(fields.nodeId) ? fields.nodeId[0] : fields.nodeId;
    
    // Robust way to get the file object with formidable v3 and multiples: false
    let fileToProcess;
    if (files.file) { // 'file' should be the name attribute from your form's file input or curl -F "file=@..."
        if (Array.isArray(files.file)) {
            if (files.file.length > 0) {
                fileToProcess = files.file[0]; 
            }
        } else {
            fileToProcess = files.file; 
        }
    }

    if (!fileToProcess) {
        console.log("[API /api/upload] No file object found in upload under 'file' field. Check curl command or form field name.");
        return res.status(400).json({ error: "No file uploaded or incorrect field name." });
    }
    const file = fileToProcess; // Now 'file' is the File object

    if (!title || !nodeIdString) {
        console.log("[API /api/upload] Missing title or nodeId in form fields.");
        return res.status(400).json({ error: "Title and nodeId are required." });
    }
    const nodeId = parseInt(nodeIdString);
    if (isNaN(nodeId)) {
        console.log("[API /api/upload] Invalid nodeId provided.");
        return res.status(400).json({ error: "Invalid nodeId." });
    }

    console.log(`[API /api/upload] Checking permission for user ${currentUser.id} to upload to node ${nodeId}.`);
    const access = await db.access.findFirst({
      where: { 
        userId: currentUser.id, 
        nodeId: nodeId, 
        role: { in: ["ADMIN", "EDITOR"] } 
      }
    });

    if (!access) {
      console.log(`[API /api/upload] User ${currentUser.email} does not have ADMIN/EDITOR access on node ${nodeId}. Sending 403.`);
      return res.status(403).json({ error: "Permission denied to upload to this folder." });
    }
    console.log(`[API /api/upload] User has ${access.role} access on node ${nodeId}. Proceeding with upload.`);

    try {
      const fileContent = fs.readFileSync(file.filepath); 
      const uniqueFilename = `${uuidv4()}_${file.originalFilename}`;
      const supabaseBucket = "docnest-uploads"; 

      console.log(`[API /api/upload] Uploading ${uniqueFilename} to Supabase bucket ${supabaseBucket}.`);
      const { data: uploadData, error: uploadError } = await supabase.storage
        .from(supabaseBucket)
        .upload(uniqueFilename, fileContent, {
          contentType: file.mimetype,
          upsert: false, 
        });

      if (uploadError) {
        console.error("[API /api/upload] Supabase upload error:", uploadError);
        throw new Error(`Supabase upload failed: ${uploadError.message}`);
      }
      
      const fileUrl = `${supabaseUrl}/storage/v1/object/public/${supabaseBucket}/${uploadData.path}`;
      console.log(`[API /api/upload] File uploaded to Supabase. URL: ${fileUrl}`);

      const artifact = await db.artifact.create({
        data: {
          title: title,
          description: description || null,
          link: fileUrl,
          nodeId: nodeId,
          createdBy: currentUser.id, // Ensure Artifact model has 'createdBy'
        },
      });
      console.log("[API /api/upload] Artifact created in database:", artifact);

      await db.access.create({
        data: { userId: currentUser.id, artifactId: artifact.id, role: "ADMIN" }
      });
      console.log(`[API /api/upload] Granted ADMIN access on new artifact ${artifact.id} to user ${currentUser.id}.`);

      return res.status(200).json({ message: "File uploaded and artifact created successfully.", artifact });
    } catch (e) {
      console.error("[API /api/upload] Error during file processing or DB operation:", e);
      return res.status(500).json({ error: "Failed to process file upload.", details: e.message });
    } finally {
        // Clean up the temporary file formidable created
        if (file && file.filepath) {
            fs.unlink(file.filepath, (unlinkErr) => {
                if (unlinkErr) console.error("[API /api/upload] Error deleting temp file:", unlinkErr.message);
                else console.log("[API /api/upload] Temp file deleted:", file.filepath);
            });
        }
    }
  });
}
