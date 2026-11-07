import { describe, expect, it } from "vitest";
import { evaluateWorldAddress } from "@/features/agents/utils/evaluateWorldAddress";

describe("evaluateWorldAddress", () => {
  it("is yellow when a web client application has no keys", () => {
    const result = evaluateWorldAddress(
      { toolId: "web_client", config: {} },
      null,
      { credentialsReady: true },
    );
    expect(result.status).toBe("yellow");
    expect(result.reason).toBe("Приложение не заполнено");
  });

  it("is yellow when the application is saved but the connection was not checked", () => {
    const result = evaluateWorldAddress(
      { toolId: "web_client", credentialId: "cred-1", config: {} },
      { meta: {} },
      { credentialsReady: true },
    );
    expect(result.status).toBe("yellow");
    expect(result.reason).toBe("Связь ещё не проверена");
  });

  it("is red when the connection check returned 404", () => {
    const result = evaluateWorldAddress(
      { toolId: "web_client", credentialId: "cred-1", config: {} },
      { meta: { verified: false, health_status: 404 } },
      { credentialsReady: true },
    );
    expect(result.status).toBe("red");
    expect(result.reason).toBe("Проверка связи не прошла: HTTP 404");
  });

  it("is red when the application keys are missing", () => {
    const result = evaluateWorldAddress(
      { toolId: "web_client", credentialId: "cred-gone", config: {} },
      null,
      { credentialsReady: true },
    );
    expect(result.status).toBe("red");
    expect(result.reason).toBe("Ключи приложения не найдены");
  });

  it("is green when the connection check passed", () => {
    const result = evaluateWorldAddress(
      { toolId: "web_client", credentialId: "cred-1", config: {} },
      { meta: { verified: true, health_status: 200 } },
      { credentialsReady: true },
    );
    expect(result.status).toBe("green");
    expect(result.reason).toBe("Приложение готово");
  });

  it("stays yellow for a telegram address without a chat id", () => {
    expect(
      evaluateWorldAddress({ toolId: "telegram", config: { chat_id: "  " } }, null).status,
    ).toBe("yellow");
  });

  it("is green for a telegram address with a chat id", () => {
    const result = evaluateWorldAddress(
      { toolId: "telegram", config: { chat_id: "-1001" } },
      null,
    );
    expect(result.status).toBe("green");
    expect(result.reason).toBe("Адрес готов");
  });
});