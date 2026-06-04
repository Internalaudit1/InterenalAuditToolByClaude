import http from "node:http";

const PUBLIC_PORT = Number(process.env.APP_PORT_INTERNAL || 3000);
const API_PORT = Number(process.env.API_INTERNAL_PORT || 8000);
const WEB_PORT = Number(process.env.WEB_INTERNAL_PORT || 3100);

const apiPrefixes = ["/api/", "/docs/", "/redoc/"];
const apiExact = new Set(["/docs", "/openapi.json", "/redoc", "/health"]);

function isApiRequest(urlPath = "/") {
  return apiExact.has(urlPath) || apiPrefixes.some((prefix) => urlPath.startsWith(prefix));
}

function proxyRequest(req, res, targetPort) {
  const proxy = http.request(
    {
      hostname: "127.0.0.1",
      port: targetPort,
      path: req.url,
      method: req.method,
      headers: {
        ...req.headers,
        host: req.headers.host ?? `127.0.0.1:${PUBLIC_PORT}`,
        "x-forwarded-host": req.headers.host ?? `127.0.0.1:${PUBLIC_PORT}`,
        "x-forwarded-port": String(PUBLIC_PORT),
        "x-forwarded-proto": "http",
      },
    },
    (upstream) => {
      res.writeHead(upstream.statusCode ?? 502, upstream.headers);
      upstream.pipe(res);
    },
  );

  proxy.on("error", (error) => {
    if (res.headersSent) {
      res.destroy(error);
      return;
    }
    res.writeHead(502, { "content-type": "application/json" });
    res.end(JSON.stringify({ detail: "Upstream service unavailable." }));
  });

  req.pipe(proxy);
}

const server = http.createServer((req, res) => {
  const targetPort = isApiRequest(req.url) ? API_PORT : WEB_PORT;
  proxyRequest(req, res, targetPort);
});

server.on("clientError", (_error, socket) => {
  socket.end("HTTP/1.1 400 Bad Request\r\n\r\n");
});

server.listen(PUBLIC_PORT, "0.0.0.0", () => {
  console.log(`Proxy listening on http://0.0.0.0:${PUBLIC_PORT}`);
});
