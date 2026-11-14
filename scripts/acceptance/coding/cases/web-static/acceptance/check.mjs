// 独立验收：直接 import logic.mjs 验证纯函数，不依赖 Agent 自写的测试。

import { pathToFileURL } from "node:url";
import { join } from "node:path";

const failures = [];
function check(name, fn) {
  try {
    const ok = fn();
    console.log(`${ok ? "PASS" : "FAIL"} ${name}`);
    if (!ok) failures.push(name);
  } catch (error) {
    console.log(`FAIL ${name}: ${error}`);
    failures.push(name);
  }
}

const logic = await import(pathToFileURL(join(process.cwd(), "logic.mjs")).href);

check("addTask 基本添加", () => {
  const tasks = logic.addTask([], "a");
  return Array.isArray(tasks) && tasks.length === 1 && tasks[0].title === "a" && tasks[0].done === false;
});
check("addTask id 唯一", () => {
  const first = logic.addTask([], "a");
  const second = logic.addTask(first, "b");
  return second[0].id !== second[1].id;
});
check("addTask 去空白", () => {
  const tasks = logic.addTask([], "  b  ");
  return tasks[0].title === "b";
});
check("addTask 空标题抛错", () => {
  try {
    logic.addTask([], "   ");
    return false;
  } catch {
    return true;
  }
});
check("toggleTask 切换", () => {
  const tasks = logic.addTask([], "a");
  const toggled = logic.toggleTask(tasks, tasks[0].id);
  return toggled[0].done === true && toggled.length === 1;
});
check("filterTasks 三种模式", () => {
  let tasks = logic.addTask([], "a");
  tasks = logic.addTask(tasks, "b");
  tasks = logic.toggleTask(tasks, tasks[0].id);
  return (
    logic.filterTasks(tasks, "all").length === 2 &&
    logic.filterTasks(tasks, "done").length === 1 &&
    logic.filterTasks(tasks, "active").length === 1
  );
});
check("formatTime 65 秒", () => logic.formatTime(65) === "01:05");
check("formatTime 0 秒", () => logic.formatTime(0) === "00:00");
check("formatTime 负数抛错", () => {
  try {
    logic.formatTime(-1);
    return false;
  } catch {
    return true;
  }
});

console.log("独立验收：", failures.length === 0 ? "PASS" : `FAIL ${failures.length} 项`);
process.exit(failures.length === 0 ? 0 : 1);
