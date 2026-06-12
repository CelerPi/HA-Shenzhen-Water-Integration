#!/usr/bin/env node

const crypto = require("crypto");
const fs = require("fs");
const path = require("path");

const BASE_URL = "https://szgk.sz-water.com.cn/api/wechat/";
const ORIGIN = "https://www.82137777.com";
const DEFAULT_CONFIG = path.join(__dirname, "sz-water.config.json");
const CHARS = "abacdefghjklmnopqrstuvwxyzABCDEFGHJKLMNOPQRSTUVWXYZ0123456789";

function randomHeader(length = 32) {
  let value = "";
  for (let index = 0; index < length; index += 1) {
    let charIndex = Math.floor(Math.random() * CHARS.length);
    if (index === 0 && charIndex >= CHARS.length - 10) {
      charIndex = Math.floor(Math.random() * (CHARS.length - 10));
    }
    value += CHARS[charIndex];
  }
  return value;
}

function keyFromHeader(header) {
  return Buffer.from(`33F4A3D6${header.slice(8, 24)}A9E19798`, "utf8");
}

function encryptPayload(payload, requestHeader) {
  const cipher = crypto.createCipheriv("aes-256-ecb", keyFromHeader(requestHeader), null);
  cipher.setAutoPadding(true);
  return Buffer.concat([
    cipher.update(JSON.stringify(payload), "utf8"),
    cipher.final(),
  ]).toString("base64");
}

function decryptResponse(body, responseHeader) {
  let encrypted = String(body).trim();
  if (encrypted.startsWith('"') && encrypted.endsWith('"')) {
    encrypted = JSON.parse(encrypted);
  }
  encrypted = encrypted.slice(0, 7) + encrypted.substring(20) + encrypted.slice(7, 20);
  const decipher = crypto.createDecipheriv("aes-256-ecb", keyFromHeader(responseHeader), null);
  decipher.setAutoPadding(true);
  const plain = Buffer.concat([
    decipher.update(encrypted, "base64"),
    decipher.final(),
  ]).toString("utf8");
  return JSON.parse(plain);
}

function readConfig(configPath = DEFAULT_CONFIG) {
  if (!fs.existsSync(configPath)) {
    throw new Error(`Config not found: ${configPath}`);
  }
  return JSON.parse(fs.readFileSync(configPath, "utf8"));
}

function writeConfig(config, configPath = DEFAULT_CONFIG) {
  fs.writeFileSync(configPath, `${JSON.stringify(config, null, 2)}\n`);
}

async function invoke(endpoint, payload, config, { token = config.token } = {}) {
  const requestHeader = randomHeader();
  const headers = {
    "04A52C9F": requestHeader,
    "Accept": "application/json, text/plain, */*",
    "Channel": config.channel || "wt",
    "Content-Type": "application/json;charset=UTF-8",
    "Origin": ORIGIN,
    "Referer": `${ORIGIN}/`,
    "TenantId": config.tenantId,
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
  };
  if (token) {
    headers.Utoken = token;
    headers.OpenId = config.mobile;
  }

  const response = await fetch(`${BASE_URL}${endpoint}`, {
    method: "POST",
    headers,
    body: encryptPayload(payload, requestHeader),
  });
  const text = await response.text();
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${text}`);
  }
  const responseHeader = response.headers.get("04a52c9f");
  if (!responseHeader) {
    throw new Error(`Missing 04A52C9F response header: ${text}`);
  }
  return decryptResponse(text, responseHeader);
}

async function sendCode(config) {
  return invoke(
    "op/user/GenerateValidationNumV20",
    {
      validationType: 4,
      mobile: config.mobile,
      customerType: "login",
      channel: config.channel || "wt",
    },
    config,
    { token: "" },
  );
}

async function login(config, code) {
  const data = await invoke(
    "op/user/LoginV20",
    {
      mobile: config.mobile,
      validationNum: code,
      validationType: 4,
      openid: config.mobile,
      channel: config.channel || "wt",
    },
    config,
    { token: "" },
  );
  if (data.code !== 0 || !data.data?.token) {
    throw new Error(`Login failed: ${JSON.stringify(data)}`);
  }
  return {
    ...config,
    token: data.data.token,
    guid: String(data.data.guid || ""),
  };
}

async function latestBill(config) {
  if (!config.token || !config.guid) {
    throw new Error("Missing token/guid. Run login first.");
  }
  if (!Array.isArray(config.customerCodes) || config.customerCodes.length === 0) {
    throw new Error("Missing customerCodes in config.");
  }
  return invoke(
    "op/BillInfo/GetLatestBillDetails2V30",
    {
      customerType: "details",
      customercodelist: config.customerCodes,
      channel: config.channel || "wt",
      openid: config.mobile,
      guid: config.guid,
    },
    config,
  );
}

function usage() {
  console.error(`Usage:
  node scripts/sz-water.js init
  node scripts/sz-water.js send-code
  node scripts/sz-water.js login <sms-code>
  node scripts/sz-water.js latest-bill

Config:
  scripts/sz-water.config.json`);
}

async function main() {
  const command = process.argv[2];
  if (command === "init") {
    const target = DEFAULT_CONFIG;
    if (fs.existsSync(target)) {
      throw new Error(`${target} already exists`);
    }
    fs.copyFileSync(path.join(__dirname, "sz-water.config.example.json"), target);
    console.log(`Created ${target}`);
    return;
  }

  if (!command) {
    usage();
    process.exitCode = 2;
    return;
  }

  const config = readConfig();
  if (command === "send-code") {
    console.log(JSON.stringify(await sendCode(config), null, 2));
    return;
  }
  if (command === "login") {
    const code = process.argv[3];
    if (!code) {
      throw new Error("Missing SMS code");
    }
    const updated = await login(config, code);
    writeConfig(updated);
    console.log(JSON.stringify({ code: 0, message: "login ok", guid: updated.guid }, null, 2));
    return;
  }
  if (command === "latest-bill") {
    console.log(JSON.stringify(await latestBill(config), null, 2));
    return;
  }

  usage();
  process.exitCode = 2;
}

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
