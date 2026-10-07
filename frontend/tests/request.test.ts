import assert from "node:assert/strict";
import test from "node:test";
import { BodyError, boundedText } from "../lib/request.ts";

test("request reads enforce byte limits and retain valid Unicode", async () => {
  assert.equal(await boundedText(new Request("https://control.example", { method: "POST", body: "é" }), 2), "é");
  await assert.rejects(boundedText(new Request("https://control.example", { method: "POST", body: "é" }), 1),
    (error: unknown) => error instanceof BodyError && error.status === 413);
  await assert.rejects(boundedText(new Request("https://control.example", {
    method: "POST", body: new Uint8Array([255])
  }), 2), (error: unknown) => error instanceof BodyError && error.status === 422);
});
