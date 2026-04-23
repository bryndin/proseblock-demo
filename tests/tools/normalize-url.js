#!/usr/bin/env node

const input = process.argv[2];

const LOCAL_HOST = process.env.LOCAL_HOST || "localhost";
const LOCAL_PORT = process.env.LOCAL_PORT || "1315";
const LOCAL_BASE = `http://${LOCAL_HOST}:${LOCAL_PORT}`;

function normalize(u) {
  try {
    const url = new URL(u);

    const warnHost = url.hostname !== LOCAL_HOST;
    const warnPort = url.port && url.port !== LOCAL_PORT;

    if (warnHost || warnPort) {
      console.warn(
        `\x1b[33m⚠️  URL host/port mismatch. Using ${LOCAL_BASE}${url.pathname}\x1b[0m`
      );
    }

    return `${LOCAL_BASE}${url.pathname}`;
  } catch {
    return `${LOCAL_BASE}${u}`;
  }
}

console.log(normalize(input));