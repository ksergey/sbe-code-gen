// Generated simple binary encoding message codec
// Message codec generator: https://github.com/ksergey/sbe-code-gen

#pragma once

#include <algorithm>
#include <bit>
#include <cstdint>
#include <numeric>
#include <span>
#include <stdexcept>
#include <string_view>

#include "mp.h"

namespace sbe_code_gen {

template <auto N>
struct MP_Value {
  static constexpr auto value = N;
};

template <CtString Name>
struct MP_MatchName {
  template <typename T>
  using fn = MP_Bool<(T::first_type::value == Name)>;
};

template <typename Fields, std::size_t N>
using FieldByIndex = typename MP_At<Fields, MP_SizeT<N>>::second_type;

template <typename Fields, CtString N>
using FieldByName = FieldByIndex<Fields, MP_Find<Fields, MP_MatchName<N>::template fn>::value>;

namespace detail {

template <typename Fields, auto>
struct FieldAtImpl;
template <typename Fields, std::size_t N>
struct FieldAtImpl<Fields, N> {
  static_assert(N < MP_Size<Fields>::value, "field number out of range");
  using type = typename MP_At<Fields, MP_SizeT<N>>::second_type;
};
template <typename Fields, CtString Name>
struct FieldAtImpl<Fields, Name> {
  using N = MP_Find<Fields, MP_MatchName<Name>::template fn>;
  static_assert(N::value < MP_Size<Fields>::value, "field with name not found");
  using type = typename MP_At<Fields, N>::second_type;
};

} // namespace detail

template <typename Fields, auto N>
using FieldAt = typename detail::FieldAtImpl<Fields, N>::type;

struct SBEType_Type {};
struct SBEType_Enum {};
struct SBEType_Set {};
struct SBEType_Composite {};
struct SBEType_Data {};
struct SBEType_Group {};
struct SBEType_Message {};

enum class Presence { Required, Optional, Constant };

} // namespace sbe_code_gen
