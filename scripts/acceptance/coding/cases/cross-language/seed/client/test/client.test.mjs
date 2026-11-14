import test from "node:test";
import assert from "node:assert/strict";

import { displayName, userId } from "../client.mjs";

test("displayName 拼接名和姓", () => {
  assert.equal(displayName({ first: "Ada", last: "Lovelace" }), "Ada Lovelace");
});

test("displayName 去除多余空格", () => {
  assert.equal(displayName({ first: " Ada ", last: " Lovelace " }), "Ada Lovelace");
});

test("displayName 缺字段时退化", () => {
  assert.equal(displayName({ first: "Ada" }), "Ada");
  assert.equal(displayName({}), "");
});

test("userId 返回 id", () => {
  assert.equal(userId({ id: 42 }), 42);
});
