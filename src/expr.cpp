#include "expr.h"

namespace rt {

const std::vector<std::string>& varNames() {
  static const std::vector<std::string> n = {
      "time", "open", "fade", "closing", "launch", "idle", "on", "sel", "selindex", "px", "py", "pdist", "pangle",
      "page", "pages", "profile", "profiles", "items", "rings", "sticky", "numbers", "radius", "hub", "ringin", "ringout", "motion", "turn",
      "hour", "minute", "second", "tick", "day", "month", "cpu", "ram", "battery", "charging", "sound", "soundl", "soundr", "beat",
      "hot", "in", "i", "n", "a", "span", "ring", "running", "windows", "active", "group", "kid", "number", "seed", "near", "press",
      "j", "m"};
  return n;
}
int varIndex(std::string_view name) {
  auto& n = varNames();
  for (size_t i = 0; i < n.size(); i++)
    if (n[i] == name) return (int)i;
  return -1;
}
static_assert(kVarCount == 59);

namespace {

enum Code : uint8_t {
  cConst, cVar, cAdd, cSub, cMul, cDiv, cMod, cPow, cNeg, cNot, cLt, cGt, cLe, cGe, cEq, cNe, cAnd, cOr,
  cSin, cCos, cTan, cAtan2, cAbs, cSign, cFloor, cCeil, cRound, cFract, cMin, cMax, cClamp, cMix, cSmooth, cStep, cSqrt, cExp,
  cNoise, cRnd, cIf, cWave, cTri, cSat, cWrap, cOutCubic, cOutBack, cOutElastic, cOutBounce, cInOut, cDeg, cRad, cLog
};
struct Fn {
  const char* name;
  Code code;
  int args;
};
const Fn kFns[] = {{"sin", cSin, 1}, {"cos", cCos, 1}, {"tan", cTan, 1}, {"atan2", cAtan2, 2}, {"abs", cAbs, 1}, {"sign", cSign, 1},
                   {"floor", cFloor, 1}, {"ceil", cCeil, 1}, {"round", cRound, 1}, {"fract", cFract, 1}, {"mod", cMod, 2}, {"pow", cPow, 2},
                   {"min", cMin, 2}, {"max", cMax, 2}, {"clamp", cClamp, 3}, {"mix", cMix, 3}, {"lerp", cMix, 3}, {"smooth", cSmooth, 3},
                   {"step", cStep, 2}, {"sqrt", cSqrt, 1}, {"exp", cExp, 1}, {"log", cLog, 1}, {"noise", cNoise, 1}, {"rnd", cRnd, 1}, {"if", cIf, 3},
                   {"wave", cWave, 1}, {"tri", cTri, 1}, {"sat", cSat, 1}, {"wrap", cWrap, 1}, {"outcubic", cOutCubic, 1},
                   {"outback", cOutBack, 1}, {"outelastic", cOutElastic, 1}, {"outbounce", cOutBounce, 1}, {"inout", cInOut, 1},
                   {"deg", cDeg, 1}, {"rad", cRad, 1}};

float hash1(float x) {
  uint32_t h;
  memcpy(&h, &x, 4);
  h ^= h >> 16;
  h *= 0x7feb352du;
  h ^= h >> 15;
  h *= 0x846ca68bu;
  h ^= h >> 16;
  return (h & 0xFFFFFF) / 16777216.f;
}
// Smooth, endless wobble between 0 and 1.
float noise1(float x) {
  float i = floorf(x), f = x - i;
  f = f * f * (3 - 2 * f);
  return lerp(hash1(i), hash1(i + 1), f);
}
float outBounce(float t) {
  t = saturate(t);
  const float n = 7.5625f, d = 2.75f;
  if (t < 1 / d) return n * t * t;
  if (t < 2 / d) { t -= 1.5f / d; return n * t * t + 0.75f; }
  if (t < 2.5f / d) { t -= 2.25f / d; return n * t * t + 0.9375f; }
  t -= 2.625f / d;
  return n * t * t + 0.984375f;
}
float finite(float v) { return v > -1e9f && v < 1e9f ? v : 0.f; }

constexpr int kStack = 32;

}  // namespace

struct ExprParser {
  std::string_view s;
  size_t at = 0;
  std::string err;
  std::vector<Expr::Op>& ops;
  int depth = 0, stack = 0, peak = 0;

  ExprParser(std::string_view text, std::vector<Expr::Op>& o) : s(text), ops(o) {}
  bool fail(const std::string& m) {
    if (err.empty()) err = m;
    return false;
  }
  void skip() {
    while (at < s.size() && (s[at] == ' ' || s[at] == '\t' || s[at] == '\n' || s[at] == '\r')) at++;
  }
  bool eat(const char* t) {
    skip();
    size_t n = strlen(t);
    if (s.substr(at, n) != t) return false;
    at += n;
    return true;
  }
  void push(Code c, float k = 0, int arg = 0) { ops.push_back({(uint8_t)c, (int16_t)arg, k}); }
  bool op(Code c, int args) {
    if (ops.size() > 400) return fail("formula is too long");
    // constants fold into one
    bool all = c != cRnd || true;
    if (ops.size() >= (size_t)args) {
      for (int i = 0; i < args; i++) all = all && ops[ops.size() - 1 - (size_t)i].code == cConst;
      if (all) {
        Expr tmp;
        tmp.ops_.assign(ops.end() - args, ops.end());
        tmp.ops_.push_back({(uint8_t)c, (int16_t)args, 0});
        float v = tmp.eval(nullptr);
        ops.resize(ops.size() - (size_t)args);
        push(cConst, v);
        stack -= args - 1;
        return true;
      }
    }
    push(c, 0, args);
    stack -= args - 1;
    return true;
  }
  bool value(float v) {
    push(cConst, v);
    return grow();
  }
  bool grow() {
    if (++stack > peak) peak = stack;
    return peak < kStack - 2 || fail("formula is too deep");
  }

  bool primary() {
    skip();
    if (at >= s.size()) return fail("formula ends early");
    if (++depth > 40) return fail("formula is nested too deeply");
    bool ok = primary2();
    depth--;
    return ok;
  }
  bool primary2() {
    char c = s[at];
    if (c == '(') {
      at++;
      if (!ternary()) return false;
      return eat(")") || fail("missing )");
    }
    if ((c >= '0' && c <= '9') || c == '.') {
      size_t e = at;
      while (e < s.size() && ((s[e] >= '0' && s[e] <= '9') || s[e] == '.')) e++;
      std::string num(s.substr(at, e - at));
      at = e;
      return value((float)strtod(num.c_str(), nullptr));
    }
    if ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || c == '_') {
      size_t e = at;
      while (e < s.size() && (isalnum((unsigned char)s[e]) || s[e] == '_')) e++;
      std::string name(s.substr(at, e - at));
      for (auto& ch : name) ch = (char)tolower((unsigned char)ch);
      at = e;
      skip();
      if (at < s.size() && s[at] == '(') {
        at++;
        for (auto& f : kFns) {
          if (name != f.name) continue;
          for (int i = 0; i < f.args; i++) {
            if (i && !eat(",")) return fail(name + " takes " + std::to_string(f.args) + " values");
            if (!ternary()) return false;
          }
          if (!eat(")")) return fail(name + " takes " + std::to_string(f.args) + (f.args == 1 ? " value" : " values"));
          return op(f.code, f.args);
        }
        return fail("unknown function " + name);
      }
      if (name == "pi") return value(kPi);
      if (name == "tau") return value(kTau);
      int v = varIndex(name);
      if (v < 0) return fail("unknown name " + name);
      push(cVar, 0, v);
      return grow();
    }
    return fail(std::string("unexpected ") + c);
  }
  bool power() {
    if (!primary()) return false;
    if (eat("^")) {
      if (!unary()) return false;
      return op(cPow, 2);
    }
    return true;
  }
  bool unary() {
    if (++depth > 40) return fail("formula is nested too deeply");
    bool ok;
    if (eat("-")) ok = unary() && op(cNeg, 1);
    else if (eat("+")) ok = unary();
    else {
      skip();
      if (at < s.size() && s[at] == '!' && s.substr(at, 2) != "!=") {
        at++;
        ok = unary() && op(cNot, 1);
      } else {
        ok = power();
      }
    }
    depth--;
    return ok;
  }
  bool product() {
    if (!unary()) return false;
    for (;;) {
      if (eat("*")) { if (!unary() || !op(cMul, 2)) return false; }
      else if (eat("/")) { if (!unary() || !op(cDiv, 2)) return false; }
      else if (eat("%")) { if (!unary() || !op(cMod, 2)) return false; }
      else return true;
    }
  }
  bool sum() {
    if (!product()) return false;
    for (;;) {
      if (eat("+")) { if (!product() || !op(cAdd, 2)) return false; }
      else if (eat("-")) { if (!product() || !op(cSub, 2)) return false; }
      else return true;
    }
  }
  bool compare() {
    if (!sum()) return false;
    for (;;) {
      Code c;
      if (eat("<=")) c = cLe;
      else if (eat(">=")) c = cGe;
      else if (eat("==")) c = cEq;
      else if (eat("!=")) c = cNe;
      else if (eat("<")) c = cLt;
      else if (eat(">")) c = cGt;
      else return true;
      if (!sum() || !op(c, 2)) return false;
    }
  }
  bool both() {
    if (!compare()) return false;
    while (eat("&&"))
      if (!compare() || !op(cAnd, 2)) return false;
    return true;
  }
  bool either() {
    if (!both()) return false;
    while (eat("||"))
      if (!both() || !op(cOr, 2)) return false;
    return true;
  }
  bool ternary() {
    if (++depth > 40) return fail("formula is nested too deeply");
    bool ok = either();
    if (ok && eat("?")) {
      ok = ternary();
      if (ok && !eat(":")) ok = fail("missing : after ?");
      ok = ok && ternary() && op(cIf, 3);
    }
    depth--;
    return ok;
  }
};

bool Expr::parse(std::string_view text, std::string* err) {
  ops_.clear();
  if (text.size() > 600) {
    if (err) *err = "formula is too long";
    return false;
  }
  ExprParser p(text, ops_);
  bool ok = p.ternary();
  p.skip();
  if (ok && p.at != text.size()) ok = p.fail("unexpected " + std::string(text.substr(p.at, 12)));
  if (!ok) {
    ops_.clear();
    if (err) *err = p.err + " in \"" + std::string(text) + "\"";
  }
  return ok;
}

bool Expr::uses(Var v) const {
  for (auto& o : ops_)
    if (o.code == cVar && o.arg == v) return true;
  return false;
}

float Expr::eval(const float* vars) const {
  float st[kStack];
  int n = 0;
  for (auto& o : ops_) {
    switch ((Code)o.code) {
      case cConst: st[n++] = o.k; continue;
      case cVar: st[n++] = vars ? vars[o.arg] : 0.f; continue;
      default: break;
    }
    // The parser guarantees enough values on the stack.
    int args = o.arg;
    if (n < args || args < 1) return 0.f;
    float* a = st + n - args;
    float r = 0;
    switch ((Code)o.code) {
      case cAdd: r = a[0] + a[1]; break;
      case cSub: r = a[0] - a[1]; break;
      case cMul: r = a[0] * a[1]; break;
      case cDiv: r = a[1] != 0 ? a[0] / a[1] : 0; break;
      case cMod: r = a[1] != 0 ? a[0] - floorf(a[0] / a[1]) * a[1] : 0; break;
      case cPow: r = powf(std::max(0.f, a[0]), a[1]); break;
      case cNeg: r = -a[0]; break;
      case cNot: r = a[0] != 0 ? 0.f : 1.f; break;
      case cLt: r = a[0] < a[1]; break;
      case cGt: r = a[0] > a[1]; break;
      case cLe: r = a[0] <= a[1]; break;
      case cGe: r = a[0] >= a[1]; break;
      case cEq: r = fabsf(a[0] - a[1]) < 1e-5f; break;
      case cNe: r = fabsf(a[0] - a[1]) >= 1e-5f; break;
      case cAnd: r = a[0] != 0 && a[1] != 0; break;
      case cOr: r = a[0] != 0 || a[1] != 0; break;
      case cSin: r = sinf(a[0]); break;
      case cCos: r = cosf(a[0]); break;
      case cTan: r = tanf(a[0]); break;
      case cAtan2: r = atan2f(a[0], a[1]); break;
      case cAbs: r = fabsf(a[0]); break;
      case cSign: r = a[0] > 0 ? 1.f : a[0] < 0 ? -1.f : 0.f; break;
      case cFloor: r = floorf(a[0]); break;
      case cCeil: r = ceilf(a[0]); break;
      case cRound: r = floorf(a[0] + 0.5f); break;
      case cFract: r = a[0] - floorf(a[0]); break;
      case cMin: r = std::min(a[0], a[1]); break;
      case cMax: r = std::max(a[0], a[1]); break;
      case cClamp: r = std::max(a[1], std::min(a[0], a[2])); break;
      case cMix: r = a[0] + (a[1] - a[0]) * a[2]; break;
      case cSmooth: r = a[1] != a[0] ? smooth01(saturate((a[2] - a[0]) / (a[1] - a[0]))) : (a[2] >= a[0] ? 1.f : 0.f); break;
      case cStep: r = a[1] >= a[0]; break;
      case cSqrt: r = sqrtf(std::max(0.f, a[0])); break;
      case cExp: r = expf(std::min(60.f, a[0])); break;
      case cLog: r = a[0] > 0 ? std::log(a[0]) : 0.f; break;
      case cNoise: r = noise1(a[0]); break;
      case cRnd: r = hash1(a[0]); break;
      case cIf: r = a[0] != 0 ? a[1] : a[2]; break;
      case cWave: r = 0.5f + 0.5f * sinf(a[0] * kTau); break;
      case cTri: { float f = a[0] - floorf(a[0]); r = 1.f - fabsf(f * 2 - 1); break; }
      case cSat: r = saturate(a[0]); break;
      case cWrap: { float f = (a[0] + 180.f) / 360.f; r = (f - floorf(f)) * 360.f - 180.f; break; }
      case cOutCubic: { float t = 1 - saturate(a[0]); r = 1 - t * t * t; break; }
      case cOutBack: { float t = saturate(a[0]) - 1; r = 1 + 2.70158f * t * t * t + 1.70158f * t * t; break; }
      case cOutElastic: { float t = saturate(a[0]); r = t <= 0 ? 0.f : t >= 1 ? 1.f : powf(2.f, -9 * t) * sinf((t * 9 - 0.75f) * kTau / 3) + 1; break; }
      case cOutBounce: r = outBounce(a[0]); break;
      case cInOut: r = smooth01(saturate(a[0])); break;
      case cDeg: r = a[0] * 180.f / kPi; break;
      case cRad: r = a[0] * kPi / 180.f; break;
      default: break;
    }
    n -= args;
    st[n++] = finite(r);
  }
  return n ? finite(st[n - 1]) : 0.f;
}

}  // namespace rt
