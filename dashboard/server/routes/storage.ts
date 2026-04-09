import { Elysia, t } from "elysia";
import { S3Client, GetObjectCommand } from "@aws-sdk/client-s3";

const s3Client = new S3Client({
  endpoint: process.env.S3_ENDPOINT || "http://s3:8333",
  region: "us-east-1",
  credentials: {
    accessKeyId: process.env.S3_ACCESS_KEY || "cdcadmin",
    secretAccessKey: process.env.S3_SECRET_KEY || "cdcsecret",
  },
  forcePathStyle: true,
});

export const storageRoutes = new Elysia({ prefix: "/storage" })
  .get("/view/*", async ({ params, set }) => {
    try {
      const path = params["*"];
      const [bucket, ...rest] = path.split("/");
      const key = rest.join("/");

      if (!bucket || !key) {
          set.status = 400;
          return "Invalid path";
      }

      const command = new GetObjectCommand({
        Bucket: bucket,
        Key: key,
      });

      const response = await s3Client.send(command);

      if (!response.Body) {
        set.status = 404;
        return "Not Found";
      }

      // Proxy the headers
      if (response.ContentType) {
          set.headers["content-type"] = response.ContentType;
      }
      if (response.ContentLength) {
          set.headers["content-length"] = response.ContentLength.toString();
      }
      set.headers["cache-control"] = "public, max-age=31536000";

      // Return the raw response using transformToByteArray to prevent Elysia from stringifying it into JSON
      const bytes = await response.Body.transformToByteArray();
      return new Response(bytes, {
          headers: set.headers as Record<string, string>
      });
    } catch (error) {
      console.error("Storage proxy error:", error);
      set.status = 404;
      return "Image Not Found or Expired in Local Vault";
    }
  });
