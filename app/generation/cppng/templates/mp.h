// Generated simple binary encoding message codec
// Message codec generator: https://github.com/ksergey/sbe-code-gen

#pragma once

#include <array>
#include <string_view>
#include <tuple>
#include <type_traits>
#include <utility>

namespace sbe_code_gen {

// compile-time string
template <std::size_t N>
struct CtString {
  std::array<char, N> storage{};

  consteval CtString() = default;

  consteval CtString(char const* str) noexcept {
    for (std::size_t i = 0; i < N; ++i) {
      storage[i] = str[i];
    }
  }

  consteval explicit CtString(char const* str, std::size_t sz) noexcept {
    for (std::size_t i = 0; i < sz; ++i) {
      storage[i] = str[i];
    }
  }

  constexpr explicit CtString(std::string_view str) noexcept : CtString(str.data(), str.size()) {}

  [[nodiscard]] constexpr operator std::string_view() const noexcept {
    return std::string_view(storage.data(), storage.size());
  }
};

template <std::size_t N>
CtString(char const (&)[N]) -> CtString<N - 1>;

template <std::size_t N, std::size_t M>
constexpr bool operator==(CtString<N> const& a, CtString<M> const& b) noexcept {
  if constexpr (N == M) {
    return a.storage == b.storage;
  } else {
    return false;
  }
}

inline namespace literals {
template <CtString Str>
consteval auto operator""_cts() noexcept {
  return Str;
}
} // namespace literals

template <typename... Ts>
struct MP_List {};

template <typename T, T... I>
using MP_List_c = MP_List<std::integral_constant<T, I>...>;

template <std::size_t N>
using MP_SizeT = std::integral_constant<std::size_t, N>;

template <bool N>
using MP_Bool = std::bool_constant<N>;

template <CtString Str>
struct MP_Str {
  static constexpr auto value = static_cast<std::string_view>(Str);
};

template <typename K, typename V>
struct MP_Pair {
  using first_type = K;
  using second_type = V;
};

namespace detail {

template <typename L, template <typename...> typename B>
struct MP_RenameImpl;

template <template <typename...> typename L, typename... T, template <typename...> typename B>
struct MP_RenameImpl<L<T...>, B> {
  using type = B<T...>;
};

} // namespace detail

template <typename L, template <typename...> typename B>
using MP_Rename = typename detail::MP_RenameImpl<L, B>::type;

namespace detail {

template <typename S>
struct MP_FromSequenceImpl;

template <typename T, T... I>
struct MP_FromSequenceImpl<std::integer_sequence<T, I...>> {
  using type = MP_List_c<T, I...>;
};

} // namespace detail

template <typename Size>
using MP_IndexSeq = typename detail::MP_FromSequenceImpl<std::make_index_sequence<Size::value>>::type;

namespace detail {

template <typename L>
struct MP_SizeImpl;

template <template <typename...> typename L, typename... T>
struct MP_SizeImpl<L<T...>> {
  using type = MP_SizeT<sizeof...(T)>;
};

} // namespace detail

template <typename L>
using MP_Size = typename detail::MP_SizeImpl<L>::type;

namespace detail {

template <typename L, typename I>
struct MP_AtImpl;

template <template <typename...> typename L, typename... T, typename I>
struct MP_AtImpl<L<T...>, I> {
  using type = typename std::tuple_element<I::value, std::tuple<T...>>::type;
};

} // namespace detail

template <typename L, typename I>
using MP_At = typename detail::MP_AtImpl<L, I>::type;

namespace detail {

template <typename... T, typename F>
constexpr void MP_forEachImpl(MP_List<T...>, F&& fn) {
  (fn(T()), ...);
}

} // namespace detail

template <typename L, typename F>
constexpr void MP_forEach(F&& fn) {
  detail::MP_forEachImpl(MP_Rename<L, MP_List>(), std::forward<F>(fn));
}

namespace detail {

struct MP_IndexHolder {
  std::size_t index;
  bool found;

  friend constexpr MP_IndexHolder operator+(MP_IndexHolder const& v, bool found) noexcept {
    if (v.found) {
      return v;
    } else if (found) {
      return {v.index, true};
    } else {
      return {v.index + 1, false};
    }
  }
};

template <typename L, template <typename...> typename P>
struct MP_FindImpl;

template <template <typename...> typename L, typename... T, template <typename...> typename P>
struct MP_FindImpl<L<T...>, P> {
  static constexpr auto holder = MP_IndexHolder{0, false};
  using type = MP_SizeT<(holder + ... + P<T>::value).index>;
};

} // namespace detail

template <typename L, template <typename...> typename P>
using MP_Find = typename detail::MP_FindImpl<L, P>::type;

} // namespace sbe_code_gen
