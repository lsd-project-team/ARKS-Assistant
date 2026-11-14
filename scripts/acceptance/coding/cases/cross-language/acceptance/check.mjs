import { pathToFileURL } from "node:url";
import { join } from "node:path";
import assert from "node:assert/strict";

const failures = [];
function check(name, fn) {
  try {
    fn();
    console.log(`PASS ${name}`);
  } catch (error) {
    console.log(`FAIL ${name}: ${error.message}`);
    failures.push(name);
  }
}

const client = await import(pathToFileURL(join(process.cwd(), "client/client.mjs")).href);
const payload = { id: 1, first: "Ada", last: "Lovelace", full_name: "Ada Lovelace" };

check("displayName 优先 full_name", () => {
  assert.equal(client.displayName(payload), "Ada Lovelace");
});
check("displayName 回退 first/last", () => {
  assert.equal(client.displayName({ first: "Alan", last: "Turing" }), "Alan Turing");
});
check("initials 使用 full_name", () => {
  assert.equal(client.initials(payload), "AL");
});
check("initials 空名字", () => {
  assert.equal(client.initials({ full_name: "" }), "");
});
check("initials 回退 first/last", () => {
  assert.equal(client.initials({ first: "ada", last: "lovelace" }), "AL");
});
check("userId 保持", () => {
  assert.equal(client.userId(payload), 1);
});

console.log("独立验收：", failures.length === 0 ? "PASS" : `FAIL ${failures.length} 项`);
process.exit(failures.length === 0 ? 0 : 1);
