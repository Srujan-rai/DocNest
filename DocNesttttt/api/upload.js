import formidable from "formidable";
import { createClient } from "@supabase/supabase-js";
import { db } from "../lib/db.js";
import { getUserFromToken } from "../lib/auth.js";
import { v4 as uuidv4 } from "uuid";

export const config = { api: { bodyParser: false } };

const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_KEY);

export default async function handler(req, res) {
  const user = await getUserFromToken(req);
  if (!user) return res.status(401).json({ error: "Unauthorized" });

  if (req.method !== "POST") return res.status(405).end();

  const form = new formidable.IncomingForm();
  form.parse(req, async (err, fields, files) => {
    if (err) return res.status(500).json({ error: "Upload error" });

    const { title, description, nodeId } = fields;
    const file = files.file[0];
    const access = await db.access.findFirst({ where: { userId: user.id, nodeId: parseInt(nodeId), role: { in: ["ADMIN", "EDITOR"] } } });
    if (!access) return res.status(403).json({ error: "Permission denied" });

    const filename = `${uuidv4()}_${file.originalFilename}`;
    const fileContent = await fs.promises.readFile(file.filepath);
    await supabase.storage.from("docnest-uploads").upload(filename, fileContent, { contentType: file.mimetype });
    const fileUrl = `${process.env.SUPABASE_URL}/storage/v1/object/public/docnest-uploads/${filename}`;

    const artifact = await db.artifact.create({
      data: { title, description, link: fileUrl, nodeId: parseInt(nodeId), createdBy: user.id }
    });

    await db.access.create({ data: { userId: user.id, artifactId: artifact.id, role: "ADMIN" } });
    return res.json({ message: "Uploaded", artifact });
  });
}
