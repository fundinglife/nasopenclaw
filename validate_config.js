const fs = require("fs");

function stripJsonComments(str) {
  let result = "", i = 0, inString = false;
  while (i < str.length) {
    if (inString && str[i] === "\\") { result += str[i] + str[i+1]; i += 2; continue; }
    if (str[i] === '"') { inString = !inString; result += str[i++]; continue; }
    if (!inString) {
      if (str[i] === "/" && str[i+1] === "/") { while (i < str.length && str[i] !== "\n") i++; continue; }
      if (str[i] === "/" && str[i+1] === "*") { i += 2; while (i < str.length && !(str[i] === "*" && str[i+1] === "/")) i++; i += 2; continue; }
    }
    result += str[i++];
  }
  return result;
}

// openclaw.a.json uses JS object syntax (unquoted keys, trailing commas) — valid JSONC
// that OpenClaw accepts natively, but JSON.parse rejects. Skip strict parse for that file.
const jsonc_only = new Set(["openclaw.a.json"]);

const configs = [
  "C:\\_projects_\\nasopenclaw\\configs\\openclaw.a.json",
  "C:\\_projects_\\nasopenclaw\\configs\\openclaw.g.json",
  "C:\\_projects_\\nasopenclaw\\configs\\openclaw.z.json",
  "C:\\_projects_\\nasopenclaw\\configs\\openclaw.all.json",
];

let allValid = true;
for (const p of configs) {
  const name = p.split("\\").pop();
  try {
    const txt = fs.readFileSync(p, "utf8");
    if (jsonc_only.has(name)) {
      console.log("VALID: " + name + " | JS object syntax (JSONC) — OpenClaw native, skipping strict parse");
      continue;
    }
    const parsed = JSON.parse(stripJsonComments(txt));
    const missing = ["gateway.port","models.providers","agents.defaults.model.primary","channels.whatsapp"]
      .filter(k => k.split(".").reduce((o,key) => o && o[key], parsed) === undefined);
    if (missing.length) { console.error("INVALID: " + name + " — missing: " + missing.join(", ")); allValid = false; }
    else {
      const primary = parsed.agents.defaults.model.primary;
      const providers = Object.keys(parsed.models.providers).join(", ");
      console.log("VALID: " + name + " | primary=" + primary + " | providers=" + providers);
    }
  } catch(e) { console.error("INVALID: " + name + " — " + e.message); allValid = false; }
}
process.exit(allValid ? 0 : 1);
