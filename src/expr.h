// Small formulas inside skins: "sel + 6*sin(time*2)". Numbers only, no loops, no side effects.
#pragma once
#include "common.h"

namespace rt {

// Everything a skin's formula can refer to.
enum Var : int {
  // the launcher
  vTime, vOpen, vFade, vClosing, vLaunch, vIdle, vOn, vSel, vSelIndex, vPx, vPy, vPDist, vPAngle,
  vPage, vPages, vProfile, vProfiles, vItems, vRings, vSticky, vNumbers, vRadius, vHub, vRingIn, vRingOut, vMotion, vTurn,
  // the world
  vHour, vMinute, vSecond, vTick, vDay, vMonth, vCpu, vRam, vBattery, vCharging, vSound, vSoundL, vSoundR, vBeat,
  // one entry
  vHot, vIn, vI, vN, vA, vSpan, vRing, vRunning, vWindows, vActive, vGroup, vKid, vNumber, vSeed, vNear, vPress,
  // one of several copies
  vJ, vM,
  kVarCount
};
int varIndex(std::string_view name);   // -1: unknown
const std::vector<std::string>& varNames();

class Expr {
 public:
  // False with a message when the text is not a formula.
  bool parse(std::string_view text, std::string* err);
  float eval(const float* vars) const;
  bool constant() const { return ops_.size() == 1 && ops_[0].code == 0; }
  bool uses(Var v) const;

 private:
  friend struct ExprParser;
  struct Op {
    uint8_t code;
    int16_t arg;
    float k;
  };
  std::vector<Op> ops_;
};

// A number in a skin: a constant, or a formula worked out for every frame.
struct Num {
  float k = 0;
  std::shared_ptr<const Expr> e;
  Num() = default;
  Num(float v) : k(v) {}
  float get(const float* vars) const { return e ? e->eval(vars) : k; }
  bool fixed() const { return !e; }
  bool uses(Var v) const { return e && e->uses(v); }
};

}  // namespace rt
