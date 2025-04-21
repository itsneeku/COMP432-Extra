import "frida-il2cpp-bridge";

Il2Cpp.Object.prototype.toString = function () {
  try {
    return this.isNull()
      ? "null"
      : // @ts-ignore
        this.method<Il2Cpp.String>("ToString", 0).invoke().content ?? "null";
  } catch (error) {
    return "Error: ToString failed";
  }
};

Il2Cpp.perform(() => {
  const battleEngineIntegrationAssembly = Il2Cpp.domain.assembly(
    "Lettuce.Infrastructure.BattleEngineIntegration"
  );

  // On Action Request
  battleEngineIntegrationAssembly.image
    .class(
      "Lettuce.Infrastructure.BattleEngineIntegration.InternalDoActionRequest"
    )
    .method(".ctor")
    .overload(
      "Lettuce.Infrastructure.BattleEngineIntegration.DoActionRequest"
    ).implementation = function (doActionRequest: any) {
    if (
      doActionRequest.method("get_SenderPlayerId").invoke().toString() == "1"
    ) {
      const actions = doActionRequest.field("Actions").value;

      for (let i = 0; i < actions.length; i++) {
        send({
          content: actions.get(i).method("ToString").invoke().toString(),
          type: "actionTaken",
        });
      }
    }

    return this.method(".ctor")
      .overload(
        "Lettuce.Infrastructure.BattleEngineIntegration.DoActionRequest"
      )
      .invoke(doActionRequest);
  };

  // On Action Response
  battleEngineIntegrationAssembly.image
    .class("Lettuce.Infrastructure.BattleEngineIntegration.LocalBattleClient")
    .method("GetHints").implementation = function (nextactioninfo) {
    send({ content: nextactioninfo.toString(), type: "getHints" });

    const gameRecord = Il2Cpp.gc.choose(
      Il2Cpp.domain
        .assembly("Lettuce.BattleEngine.Serialization.Runtime")
        .image.class("Lettuce.BattleEngine.Schema.GameRecord")
    )[0];
    send({ content: gameRecord.toString(), type: "gameRecord" });

    return this.method("GetHints").invoke(nextactioninfo);
  };
});
