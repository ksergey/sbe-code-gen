// ------------------------------------------------------------
// Copyright 2022-present Sergey Kovalevich <inndie@gmail.com>
// ------------------------------------------------------------

#include <cstddef>
#include <cstdio>
#include <iostream>
#include <print>
#include <span>
#include <string_view>
#include <type_traits>

#include "schema.h"

namespace content {

#include "Binance_exchangeInfo_data.h"
#include "Binance_ticker_data.h"

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
        [[maybe_unused]] auto buffer1 = std::span<std::byte>(
            std::bit_cast<std::byte*>((unsigned char*)content::exchangeInfo), content::exchangeInfo_len);
        [[maybe_unused]] auto buffer2 =
            std::span<std::byte>(std::bit_cast<std::byte*>((unsigned char*)content::ticker), content::ticker_len);

        auto header = spot_sbe::MessageHeader{buffer2.data()};
        std::print("header: {}\n", header);
        if (header.get<"templateId">().value() == spot_sbe::Ticker24hFullResponse::sbeTemplateId()) {
            auto body = spot_sbe::Ticker24hFullResponse(buffer2, header.sbeEncodedLength(),
                header.get<"blockLength">().value(), header.get<"version">().value());
            std::print("body: {}\n", body);
        }

#if 0
        spot_sbe::decode(buffer2, [](auto msg) {
            Printer::print(std::cout, msg, msg.sbeMessageName());
        });
        spot_sbe::decode(buffer2, [](auto msg) {
            std::cout << msg.asJson().dump(2) << '\n';
        });
#endif
    } catch (std::exception const& e) {
        std::print(stderr, "ERROR: {}\n", e.what());
        return EXIT_FAILURE;
    }
    return EXIT_SUCCESS;
}
