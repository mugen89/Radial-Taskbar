// Interface sounds: the skin's own when it has some, otherwise small synthesised ones.
#pragma once
#include <string>

namespace rt {
enum class Sound { Open, Tick, Launch, Close, Profile };
void playSound(Sound s, float volume);
}  // namespace rt
