// SPDX-FileCopyrightText: Copyright DB InfraGO AG and the capellambse-context-diagrams contributors
// SPDX-License-Identifier: Apache-2.0

import { createInterface } from "node:readline";
import process from "node:process";
import ELK from "npm:elkjs";
import { ElkGraphJsonToSprotty } from "./elkgraph-to-sprotty.ts";
await import("npm:elkjs/lib/elk-worker.min.js"); // initialize the ELK layout engine

interface Message {
  id?: string;
  cmd?: string;
  [key: string]: any;
}

interface MessageEvent {
  data: Message;
}

/**
 * FakeWorker implementation for ELK.js in Deno environment.
 * Bridges ELK's worker-based architecture with synchronous execution.
 */
class FakeWorker {
  onmessage: ((event: MessageEvent) => void) | null = null;

  postMessage(msg: Message): void {
    setTimeout(() => {
      try {
        const globalSelf = globalThis as any;

        if (globalSelf.onmessage) {
          const originalPostMessage = globalSelf.postMessage;

          globalSelf.postMessage = (responseMsg: Message) => {
            if (this.onmessage) {
              this.onmessage({ data: responseMsg });
            }
          };

          globalSelf.onmessage({ data: msg });
          globalSelf.postMessage = originalPostMessage;
        } else {
          throw new Error(
            "ELK worker not initialized: globalThis.onmessage is undefined"
          );
        }
      } catch (err) {
        if (this.onmessage) {
          this.onmessage({
            data: {
              id: msg.id,
              error: err instanceof Error ? err.message : String(err),
            },
          });
        }
      }
    }, 0);
  }

  terminate(): void {
    this.onmessage = null;
  }
}

const elk = new ELK({
  workerFactory: () => new FakeWorker(),
});

console.log("--- ELK layouter started ---");

for await (const line of createInterface({ input: process.stdin })) {
  const input = JSON.parse(line);
  const layouted = await elk.layout(input);
  const transformed = new ElkGraphJsonToSprotty().transform(layouted);
  console.log(JSON.stringify(transformed));
}
