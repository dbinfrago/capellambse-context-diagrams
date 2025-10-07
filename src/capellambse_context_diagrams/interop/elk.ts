// SPDX-FileCopyrightText: Copyright DB InfraGO AG and the capellambse-context-diagrams contributors
// SPDX-License-Identifier: Apache-2.0

import { createInterface } from "node:readline";
import process from "node:process";
import ELK from "npm:elkjs@^0.11.0";
import { ElkGraphJsonToSprotty } from "./elkgraph-to-sprotty.ts";
await import("npm:elkjs@^0.11.0/lib/elk-worker.min.js"); // initialize the ELK layout engine

interface MessageEvent {
  data: {
    id?: string;
    cmd?: string;
    [key: string]: any;
  };
}

/**
 * FakeWorker implementation for ELK.js in Deno environment.
 * Bridges ELK's worker-based architecture with synchronous execution.
 */
class FakeWorker {
  onmessage: ((event: MessageEvent) => void) | null = null;
  private messageHandler: (event: MessageEvent) => void;

  constructor() {
    this.messageHandler = (event: MessageEvent) => {
      const data = event.data;

      try {
        const globalSelf = globalThis as any;

        if (globalSelf.onmessage) {
          const originalPostMessage = globalSelf.postMessage;

          globalSelf.postMessage = (msg: any) => {
            if (this.onmessage) {
              this.onmessage({ data: msg });
            }
          };

          globalSelf.onmessage(event);
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
              id: data.id,
              error: err instanceof Error ? err.message : String(err),
            },
          });
        }
      }
    };
  }

  postMessage(msg: any): void {
    setTimeout(() => {
      this.messageHandler({ data: msg });
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
