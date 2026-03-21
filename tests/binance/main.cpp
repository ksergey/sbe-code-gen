// ------------------------------------------------------------
// Copyright 2022-present Sergey Kovalevich <inndie@gmail.com>
// ------------------------------------------------------------

#include <cstddef>
#include <cstdio>
#include <iostream>
#include <span>
#include <string_view>
#include <type_traits>

#include "schema.h"

namespace content {

#include "Binance_exchangeInfo_data.h"

} // namespace content

template <typename N>
std::ostream& operator<<(std::ostream& os, std::span<N const> const& value) {
    os << '[';
    bool atLeastOnePrinted{false};
    for (auto const& v : value) {
        if (atLeastOnePrinted) {
            os << ", ";
        }
        os << int(v);
        atLeastOnePrinted = true;
    }
    os << ']';
    return os;
}

struct Printer {
    template <typename FieldT>
        requires(requires { std::declval<FieldT>().value(); })
    static void print(std::ostream& os, FieldT field, std::string_view parent) {
        if (!parent.empty()) {
            os << parent << '.';
        }
        os << field.sbeRefName() << ": ";
        if (field.present()) {
            os << field.value() << '\n';
        } else {
            os << "N/A\n";
        }
    }

    template <typename AggrT>
        requires(requires { typename AggrT::Fields; })
    static void print(std::ostream& os, AggrT aggr, std::string_view parent = {}) {
        std::string prefix{parent};
        if constexpr (requires { aggr.sbeRefName(); }) {
            prefix.append(".").append(aggr.sbeRefName());
        }

        auto printFields = [&]<template <typename...> typename L, typename... Ts>(L<Ts...>, std::string_view prefix) {
            if constexpr (sizeof...(Ts) > 0) {
                [&]<std::size_t... I>(std::index_sequence<I...>) {
                    (Printer::print(os, aggr.template get<I>(), prefix), ...);
                }(std::make_index_sequence<sizeof...(Ts)>{});
            } else {
                os << "No fields\n";
            }
        };

        if constexpr (requires { aggr.sbeGroupName(); }) {
            std::size_t index = 0;
            while (aggr.hasNext()) {
                aggr.next();
                printFields(typename AggrT::Fields{}, prefix + "[" + std::to_string(index++) + "]");
            }

        } else {
            printFields(typename AggrT::Fields{}, prefix);
        }
    }
};

int main([[maybe_unused]] int argc, [[maybe_unused]] char* argv[]) {
    try {
        auto buffer = std::span<std::byte>(std::bit_cast<std::byte*>((unsigned char*)content::binance_exchangeInfo_sbe),
            content::binance_exchangeInfo_sbe_len);
        spot_sbe::decode(buffer, [](auto msg) {
            Printer::print(std::cout, msg);
        });
    } catch (std::exception const& e) {
        std::cerr << "ERROR: " << e.what() << '\n';
        return EXIT_FAILURE;
    }
    return EXIT_SUCCESS;
}
