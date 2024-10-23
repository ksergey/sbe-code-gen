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

enum class Presence { Required, Optional, Constant };

template <auto N>
struct MP_Value {
  static constexpr auto value = N;
};

struct MP_None {};

template <CtString Name, auto Value>
struct MP_Choice {
  static constexpr auto name = Name;
  static constexpr auto value = Value;
};

template <CtString Name, auto Value>
struct MP_ValidValue {
  static constexpr auto name = Name;
  static constexpr auto value = Value;
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

template <typename T>
class Encoding;

template <typename T>
  requires(std::derived_from<T, SBEType_Type>)
struct Encoding<T> {
  using value_type = typename T::value_type;
  using primitive_type = typename T::primitive_type;

  [[nodiscard]] static constexpr bool present(std::byte const* buffer) noexcept {
    auto const value = *std::bit_cast<primitive_type const*>(buffer);
    if constexpr (std::is_floating_point_v<T>) {
      // in case of nullValue is NaN
      if constexpr (T::nullValue != T::nullValue) {
        return !(value != value);
      }
    }
    return value != T::nullValue;
  }

  [[nodiscard]] static constexpr value_type value(std::byte const* buffer) noexcept {
    auto const ptr = std::bit_cast<primitive_type const*>(buffer);
    if constexpr (T::length > 1) {
      if constexpr (std::is_same_v<value_type, std::string_view>) {
        // strings: trim from \0
        std::string_view str(ptr, T::length);
        return str.substr(0, str.find('\0'));
      } else {
        return value_type(ptr, T::length);
      }
    } else {
      return value_type(*ptr);
    }
  }

  static constexpr void value(std::byte* buffer, value_type value) noexcept {
    auto const ptr = std::bit_cast<primitive_type*>(buffer);
    if constexpr (T::length > 1) {
      if constexpr (std::is_same_v<value_type, std::string_view>) {
        std::fill(std::copy(value.begin(), value.end(), ptr), ptr + T::length, char('\0'));
      } else {
        std::copy_n(value.data(), T::length, ptr);
      }
    } else {
      *ptr = value;
    }
  }

  constexpr void reset(std::byte* buffer) noexcept {
    auto const ptr = std::bit_cast<primitive_type*>(buffer);
    *ptr = T::nullValue;
  }
};

template <typename T>
  requires(std::derived_from<T, SBEType_Enum> or std::derived_from<T, SBEType_Set>)
struct Encoding<T> {
  using primitive_type = typename T::primitive_type;
  using value_type = T;

  [[nodiscard]] static constexpr bool present(std::byte const* buffer) noexcept {
    return value(buffer) != T::NULL_VALUE;
  }

  [[nodiscard]] static constexpr T value(std::byte const* buffer) noexcept {
    auto const ptr = std::bit_cast<primitive_type const*>(buffer);
    return T(*ptr);
  }

  static constexpr void value(std::byte* buffer, value_type value) noexcept {
    auto const ptr = std::bit_cast<primitive_type*>(buffer);
    *ptr = value.rawValue();
  }

  constexpr void reset() noexcept {
    this->setValue(T());
  }
  constexpr void reset(std::byte* buffer) noexcept {
    value(buffer, T());
  }
};

namespace detail {

template <typename T>
struct EncodingTypeImpl : std::false_type {};
template <typename T>
struct EncodingTypeImpl<Encoding<T>> : std::true_type {};

} // namespace detail

template <typename T>
concept EncodingType = detail::EncodingTypeImpl<T>::value;

template <typename T>
  requires(std::derived_from<T, SBEType_Composite>)
class Data : public SBEType_Data {
private:
  std::byte* buffer_ = nullptr;
  std::size_t bufferLength_ = 0;
  std::size_t initialPosition_ = 0;
  std::size_t* positionPtr_ = nullptr;
  std::uint16_t actingVersion_ = 0;

public:
  using encoding_type = T;
  using VarData = FieldByName<typename T::Fields, "varData">;

  constexpr Data() = default;

  constexpr Data(std::byte* buffer, std::size_t* pos, std::size_t bufferLength, std::uint16_t actingVersion)
      : buffer_(buffer), bufferLength_(bufferLength), initialPosition_(*pos), positionPtr_(pos),
        actingVersion_(actingVersion) {
    *positionPtr_ = *positionPtr_ + T::encodedLength();
  }

  [[nodiscard]] constexpr typename VarData::value_type value() {
    auto const size = T(buffer_, initialPosition_, bufferLength_, actingVersion_).template field<"length">().value();
    auto const result = typename VarData::value_type(
        std::bit_cast<typename VarData::primitive_type*>(buffer_ + initialPosition_ + T::encodedLength()), size);
    this->sbePosition(initialPosition_ + T::encodedLength() + size * sizeof(typename VarData::primitive_type));
    return result;
  }

  constexpr void setValue(typename VarData::value_type value) {
    T(buffer_, initialPosition_, bufferLength_, actingVersion_).template field<"length">().setValue(value.size());
    std::copy(value.begin(), value.end(),
        std::bit_cast<typename VarData::primitive_type*>(buffer_ + initialPosition_ + T::encodedLength()));
    this->sbePosition(initialPosition_ + T::encodedLength() + value.size() * sizeof(typename VarData::primitive_type));
  }

  constexpr std::size_t sbeCheckPosition(std::size_t position) const {
    if (position > bufferLength_) [[unlikely]] {
      throw std::runtime_error("buffer too short [E100]");
    }
    return position;
  }

  constexpr void sbePosition(std::size_t position) {
    *positionPtr_ = this->sbeCheckPosition(position);
  }
};

template <typename T, typename PresenceT, typename OffsetT, typename ConstValueT = MP_None>
class FieldEncoding;

template <typename T, typename PresenceT, typename OffsetT, typename ConstValueT>
  requires(EncodingType<T>)
class FieldEncoding<T, PresenceT, OffsetT, ConstValueT> {
private:
  std::byte* buffer_ = nullptr;

public:
  using value_type = T::value_type;
  using primitive_type = T::primitive_type;

  constexpr FieldEncoding(std::byte* buffer, std::size_t offset, [[maybe_unused]] std::size_t bufferLength,
      [[maybe_unused]] std::uint16_t actingVersion) noexcept
      : buffer_(buffer + offset + OffsetT::value) {}

  [[nodiscard]] constexpr bool present() const noexcept {
    if constexpr (PresenceT::value == Presence::Optional) {
      return T::present(buffer_);
    } else {
      return true;
    }
  }

  [[nodiscard]] constexpr value_type value() const noexcept {
    if constexpr (PresenceT::value != Presence::Constant) {
      return T::value(buffer_);
    } else {
      return ConstValueT::value;
    }
  }

  constexpr void setValue(value_type value) noexcept {
    if constexpr (PresenceT::value != Presence::Constant) {
      T::value(buffer_, value);
    } else {
      if (value != ConstValueT::value) [[unlikely]] {
        throw std::runtime_error("constant value mismatch");
      }
    }
  }

  constexpr void reset() noexcept {
    if constexpr (PresenceT::value != Presence::Constant and PresenceT::value != Presence::Required) {
      T::reset(buffer_);
    } else {
      throw std::runtime_error("reset not available");
    }
  }
};

template <typename T, typename PresenceT, typename OffsetT, typename ConstValueT>
  requires(std::derived_from<T, SBEType_Composite>)
class FieldEncoding<T, PresenceT, OffsetT, ConstValueT> : public T {
public:
  using value_type = T;

  using T::T;

  [[nodiscard]] constexpr bool present() noexcept {
    if constexpr (PresenceT::value == Presence::Optional) {
      return this->template field<0>().present();
    } else {
      return true;
    }
  }

  constexpr void reset() noexcept {
    if constexpr (PresenceT::value != Presence::Constant and PresenceT::value != Presence::Required) {
      this->template field<0>().reset();
    } else {
      throw std::runtime_error("reset not available");
    }
  }
};

template <typename T, typename PresenceT, typename OffsetT, typename ConstValueT>
  requires(std::derived_from<T, SBEType_Group> or std::derived_from<T, SBEType_Data>)
class FieldEncoding<T, PresenceT, OffsetT, ConstValueT> : public T {
public:
  using value_type = T;

  using T::T;
};

} // namespace sbe_code_gen
